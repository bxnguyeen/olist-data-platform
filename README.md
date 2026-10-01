# Pipeline dữ liệu Olist — Báo cáo tiến độ triển khai

## 1. Mục tiêu

Xây dựng pipeline dữ liệu ba tầng, sử dụng dbt làm công cụ biến đổi:

**`01_raw` → `02_stg` → `03_data_warehouse`**

Phiên bản hiện tại xử lý dữ liệu đơn hàng và khách hàng từ bộ Olist Brazilian E-Commerce.

## 2. Kiến trúc

```text
Các file CSV nguồn
    ↓ Upload thủ công
MinIO lưu trữ file
    ↓ Python đọc theo luồng và nạp dữ liệu
PostgreSQL: 01_raw
    ↓ dbt chuẩn hóa
PostgreSQL: 02_stg
    ↓ dbt xây dựng bảng nghiệp vụ
PostgreSQL: 03_data_warehouse
```

| Thành phần | Vai trò |
|---|---|
| MinIO | Lưu các file CSV gốc |
| Python | Đọc file từ MinIO, kiểm tra cấu trúc và nạp vào PostgreSQL |
| PostgreSQL | Lưu cả ba tầng dữ liệu và thực thi SQL |
| dbt Core | Quản lý phép biến đổi SQL, phụ thuộc giữa model và kiểm tra dữ liệu |
| Docker Compose | Vận hành MinIO riêng cho dự án |
| VS Code / DBeaver | Hỗ trợ phát triển và kiểm tra kết quả |

PostgreSQL chạy riêng qua Postgres.app trên macOS. Phiên bản hiện tại chưa sử dụng Trino.

## 3. Các tầng dữ liệu

### `01_raw` — Dữ liệu giữ sát nguồn

Gồm hai bảng: `orders`, `customers`.

Mỗi bảng có **99.441 dòng**. Các cột được lưu dưới dạng text để giữ cách biểu diễn của nguồn, bao gồm mã định danh và tiền tố mã bưu chính. File CSV gốc vẫn được lưu trong MinIO.

### `02_stg` — Dữ liệu được chuẩn hóa

Gồm hai model: `stg_orders`, `stg_customers`.

Các phép biến đổi gồm chuẩn hóa tên cột, chuyển ngày giờ đơn hàng sang timestamp, bỏ khoảng trắng đầu/cuối, chuẩn hóa chữ hoa/thường của thông tin địa điểm và chuyển chuỗi rỗng thành NULL tại các cột được quy định.

### `03_data_warehouse` — Dữ liệu phục vụ nghiệp vụ

**`fct_orders`: một dòng cho mỗi đơn hàng**

Lưu thông tin đơn, mã khách hàng, thời gian giao hàng, trạng thái giao trễ và cờ thiếu ngày giao.

**`dim_customers`: một dòng cho mỗi `customer_unique_id`**

Lưu mã khách, thời điểm đặt hàng đầu tiên/gần nhất và số đơn. Các ngày và số đơn được tính trên mọi trạng thái đơn trong dataset.

Bảng khách hàng phiên bản đầu có thêm các thuộc tính tổng hợp từ đơn hàng. Chưa chọn một địa điểm mới nhất đại diện cho khách, vì địa điểm có thể khác nhau giữa các lần mua.

## 4. Cơ chế nạp và thực thi

Chương trình Python đọc CSV theo luồng vào các bảng tạm PostgreSQL, không tải toàn bộ file vào bộ nhớ Python.

Chương trình kiểm tra tên và thứ tự cột, từ chối file không có dữ liệu và sử dụng PostgreSQL COPY để đọc cấu trúc CSV, nạp các bản ghi. Sau khi cả hai bảng tạm nạp thành công, chương trình thay dữ liệu raw và đối chiếu số dòng raw với bảng tạm.

Việc thay dữ liệu hai bảng raw nằm trong cùng một giao dịch. Nếu xảy ra lỗi trước commit, các thay đổi được rollback. Chạy lại sẽ thay dữ liệu hiện có, không nối thêm các dòng trùng.

Pipeline được chạy bằng:

```bash
python scripts/run_pipeline.py
```

Chương trình điều phối nạp raw trước, sau đó chạy dbt. Nếu nạp thất bại, dbt không được khởi chạy.

## 5. Kết quả kiểm tra

Dựa trên các lần chạy đã hoàn thành:

- Hai bảng raw orders và customers đều có **99.441 dòng**.
- Dimension khách hàng có **96.096 khách phân biệt**.
- Tổng số đơn theo khách bằng **99.441 đơn**.
- Các test đã cấu hình về khóa, quan hệ và số dòng đều đạt.
- **8 đơn có trạng thái đã giao nhưng thiếu ngày giao thực tế**, được phát cảnh báo.
- Đã thử tạo lỗi sau khi làm rỗng raw; sau rollback, số dòng của cả hai bảng vẫn được giữ nguyên.

## 6. Quy tắc nghiệp vụ và giới hạn

Chỉ đánh giá giao trễ đối với đơn có trạng thái `delivered`, có đủ ngày giao thực tế và ngày giao dự kiến. So sánh theo ngày lịch, nên giao trong ngày hẹn được tính là đúng hạn. Đơn không đủ điều kiện đánh giá được giữ NULL, không mặc định là đúng hạn.

Phiên bản hiện tại nạp lại toàn bộ dữ liệu. Upload file lên MinIO và khởi chạy pipeline vẫn thực hiện thủ công; chưa thiết lập lịch chạy.

Bước nạp raw và bước chạy dbt không nằm trong một giao dịch chung. Nếu raw đã commit nhưng dbt thất bại, raw vẫn giữ dữ liệu vừa nạp.

Streaming đã được kiểm chứng với dataset hiện tại, chưa đo hiệu năng trên file hàng chục GB. Bảng tạm cần thêm dung lượng PostgreSQL. Đối chiếu số dòng không tự chứng minh file nguồn đầy đủ hoặc mọi giá trị đều chính xác.

## 7. Vai trò của dbt

dbt tổ chức SQL thành các model có thể tái sử dụng, xác định phụ thuộc qua `source()` và `ref()`, đồng thời chạy các kiểm tra dữ liệu đã khai báo. PostgreSQL thực hiện tính toán và lưu kết quả.

Bài thực hành thể hiện lợi ích của dbt so với quản lý các script SQL thủ công riêng lẻ: chạy lại có trình tự, quan hệ phụ thuộc rõ ràng và kiểm tra tự động. Python vẫn đảm nhiệm việc nạp dữ liệu.

## 8. Trạng thái hiện tại

Đã triển khai và chạy lại thành công pipeline cho đơn hàng và khách hàng, gồm nạp theo luồng, biến đổi, kiểm tra dữ liệu và thử nghiệm rollback.

Các hướng tiếp theo có thể gồm mở rộng kiểm tra chất lượng, hoàn thiện khả năng tái tạo môi trường, lập lịch chạy và bổ sung các bảng nguồn khác.



# Olist Data Pipeline — Implementation Progress Report

## 1. Objective

Build a three-layer data pipeline using dbt for data transformation:

**`01_raw` → `02_stg` → `03_data_warehouse`**

The current implementation covers orders and customers from the Olist Brazilian E-Commerce dataset.

## 2. Architecture

```text
Source CSV files
    ↓ Manual upload
MinIO object storage
    ↓ Python streaming ingestion
PostgreSQL: 01_raw
    ↓ dbt transformations
PostgreSQL: 02_stg
    ↓ dbt business models
PostgreSQL: 03_data_warehouse
```

| Component | Responsibility |
|---|---|
| MinIO | Stores the original CSV files |
| Python | Reads files from MinIO, validates their structure and loads PostgreSQL |
| PostgreSQL | Stores all three data layers and executes SQL |
| dbt Core | Manages SQL transformations, model dependencies and data tests |
| Docker Compose | Runs the project’s MinIO service |
| VS Code / DBeaver | Support development and inspection |

PostgreSQL runs separately through Postgres.app on macOS. Trino is not part of the current implementation.

## 3. Data Layers

### `01_raw` — Source-aligned data

Tables: `orders`, `customers`.

Both tables contain **99,441 rows**. Columns are stored as text to preserve source representations, including identifiers and postal-code prefixes. Original CSV files remain available in MinIO.

### `02_stg` — Standardized data

Models: `stg_orders`, `stg_customers`.

Transformations include standardizing column names, converting order timestamps, trimming surrounding whitespace, normalizing customer location text and converting empty strings to NULL where specified.

### `03_data_warehouse` — Business-oriented data

**`fct_orders`: one row per order**

Contains order details, customer identifiers, delivery duration, late-delivery status and a missing-delivery-date flag.

**`dim_customers`: one row per `customer_unique_id`**

Contains the customer identifier, first and latest order timestamps, and order count. Dates and counts cover all order statuses in the available dataset.

This initial customer model includes aggregated order attributes. Customer location is not reduced to a single latest address, because location can differ between orders.

## 4. Ingestion and Execution

The Python loader streams CSV data into PostgreSQL temporary tables without loading entire files into Python memory.

It validates column names and order, rejects empty datasets, and uses PostgreSQL COPY to parse and load CSV records. After both temporary tables are loaded, it replaces the raw data and compares raw row counts with temporary-table counts.

Both raw-table replacements occur in one transaction. An ingestion failure before commit rolls back the changes. Repeated loads replace existing data instead of appending duplicate rows.

The pipeline runs with:

```bash
python scripts/run_pipeline.py
```

The runner loads raw data first, then invokes dbt. If ingestion fails, dbt is not started.

## 5. Validation Results

Based on the completed runs:

- Raw orders and customers each contain **99,441 rows**.
- The customer dimension contains **96,096 distinct customers**.
- Customer order counts sum to **99,441 orders**.
- Configured key, relationship and row-count tests passed.
- **8 delivered orders lack an actual delivery timestamp** and generate a warning.
- A deliberate failure after raw-table truncation was tested; both raw tables retained their previous row counts after rollback.

## 6. Business Rules and Limitations

Late delivery is evaluated only for orders marked `delivered` with both actual and estimated delivery dates available. Comparison uses calendar dates, so delivery on the promised date is considered on time. Orders that cannot be evaluated retain NULL rather than being classified as on time.

The implementation currently uses full refresh ingestion. File upload to MinIO and pipeline invocation remain manual; scheduled execution is not configured.

Raw ingestion and dbt execution are not one shared transaction. If ingestion commits and dbt subsequently fails, the refreshed raw data remains.

Streaming has been verified with the current dataset, not benchmarked on files of tens of gigabytes. Temporary tables require additional PostgreSQL storage. Row-count reconciliation does not independently prove that the source files are complete or that every value is correct.

## 7. Role of dbt

dbt organizes SQL into reusable models, resolves dependencies through `source()` and `ref()`, and executes configured data tests. PostgreSQL performs the computation and stores the results.

This demonstrates dbt’s value over separately maintained manual SQL scripts: repeatable execution, explicit dependencies and automated validation. Python remains responsible for ingestion.

## 8. Current Status

A working pipeline for orders and customers has been implemented and rerun successfully, including streaming ingestion, transformation, data testing and a rollback exercise.

Potential next steps include broader data-quality coverage, reproducible dependency setup, scheduling and additional source tables.