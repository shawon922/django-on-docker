# Bank Statement Extractor

A comprehensive Django application for extracting and managing bank statement data from PDF files and images using OCR technology, integrated with the Django on Docker project.

## Features

### Core Functionality
- **File Upload**: Drag-and-drop interface for PDF and image files
- **OCR Processing**: Extract text from images using Tesseract and PaddleOCR
- **PDF Parsing**: Extract structured data from PDF bank statements
- **Data Validation**: Clean and validate extracted transaction data
- **Transaction Management**: View, edit, and organize transactions
- **Export Options**: Export data in CSV, Excel, and JSON formats

### User Interface
- **Responsive Design**: Bootstrap-based UI that works on all devices
- **Dashboard**: Overview of statements and recent activity
- **Advanced Filtering**: Filter transactions by date, amount, type, and description
- **Real-time Processing**: Live updates on processing status
- **Bulk Operations**: Select and export multiple transactions

### Technical Features
- **Asynchronous Processing**: Background processing with Celery
- **Security**: File validation, CSRF protection, and secure uploads
- **Logging**: Comprehensive logging of all operations
- **Error Handling**: Graceful error handling and user feedback
- **Performance**: Optimized queries and caching

## Installation

### Prerequisites
- Python 3.12+
- PostgreSQL
- Redis (for Celery)
- Tesseract OCR

### System Dependencies

#### macOS
```bash
brew install tesseract
brew install poppler
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install poppler-utils
```

### Python Dependencies

The required packages are already defined in the `Pipfile`:

```toml
# Core Django packages
django = "*"
psycopg2-binary = "*"
gunicorn = "*"

# Bank statement processing
pytesseract = "*"
Pillow = "*"
pdfplumber = "*"
PyMuPDF = "*"
camelot-py = {extras = ["cv"], version = "*"}
tabula-py = "*"
pandas = "*"
numpy = "*"
openpyxl = "*"

# Django extensions
django-crispy-forms = "*"
crispy-bootstrap5 = "*"
django-extensions = "*"

# Background processing
celery = "*"
redis = "*"

# Security
cryptography = "*"
```

### Setup Instructions

1. **Install dependencies**:
   ```bash
   cd app
   pipenv install
   ```

2. **Activate virtual environment**:
   ```bash
   pipenv shell
   ```

3. **Run migrations**:
   ```bash
   python manage.py makemigrations bank_statement
   python manage.py migrate
   ```

4. **Create superuser**:
   ```bash
   python manage.py createsuperuser
   ```

5. **Collect static files**:
   ```bash
   python manage.py collectstatic
   ```

6. **Start Redis server** (in separate terminal):
   ```bash
   redis-server
   ```

7. **Start Celery worker** (in separate terminal):
   ```bash
   celery -A hello_django worker --loglevel=info
   ```

8. **Start development server**:
   ```bash
   python manage.py runserver
   ```

## Usage

### Accessing the Application

1. Navigate to `http://localhost:8000/bank-statements/`
2. You'll see the dashboard with upload options

### Uploading Bank Statements

1. Click "Upload Statement" or drag files to the upload area
2. Supported formats: PDF, JPEG, PNG, TIFF
3. Maximum file size: 50MB
4. The system will automatically process the file

### Processing Flow

1. **File Upload**: File is validated and stored
2. **OCR/PDF Extraction**: Text is extracted from the document
3. **Data Parsing**: Transaction data is identified and structured
4. **Validation**: Data is cleaned and validated
5. **Storage**: Transactions are saved to the database

### Managing Transactions

- **View All**: Browse all transactions with filtering options
- **Edit**: Modify transaction details
- **Export**: Download data in various formats
- **Search**: Find specific transactions by description
- **Filter**: Filter by date range, amount, type, or bank

## Configuration

### Settings

Key settings in `settings.py`:

```python
# File Upload Settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024  # 50MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 50 * 1024 * 1024   # 50MB

# Media Settings
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

# OCR Settings
TESSERACT_CMD = '/usr/local/bin/tesseract'  # Adjust path as needed
```

### Environment Variables

Create a `.env` file with:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
```

## API Endpoints

### Main URLs
- `/bank-statements/` - Dashboard
- `/bank-statements/upload/` - Upload statement
- `/bank-statements/statements/` - List statements
- `/bank-statements/statements/<id>/` - Statement detail
- `/bank-statements/transactions/` - List all transactions
- `/bank-statements/transactions/<id>/edit/` - Edit transaction

### AJAX Endpoints
- `/bank-statements/ajax/retry-processing/<id>/` - Retry processing
- `/bank-statements/ajax/processing-status/<id>/` - Get processing status
- `/bank-statements/export/statements/` - Export statements
- `/bank-statements/export/transactions/` - Export all transactions

## Database Models

### Statement
- File information and metadata
- Processing status and logs
- Bank information
- Date ranges

### Transaction
- Individual transaction details
- Amounts (debit/credit)
- Dates and descriptions
- Reference numbers
- Relationship to statement

### ProcessingLog
- Processing history
- Error logs
- Performance metrics

## File Structure

```
bank_statement/
├── __init__.py
├── admin.py              # Django admin configuration
├── apps.py               # App configuration
├── forms.py              # Form definitions
├── models.py             # Database models
├── urls.py               # URL patterns
├── utils.py              # Processing utilities
├── views.py              # View functions
├── migrations/           # Database migrations
├── templates/            # HTML templates
│   └── bank_statement/
│       ├── base.html
│       ├── dashboard.html
│       ├── upload_statement.html
│       ├── statement_list.html
│       ├── statement_detail.html
│       ├── transaction_list.html
│       └── transaction_edit.html
└── static/               # Static files
    └── bank_statement/
        ├── css/
        │   └── bank_statement.css
        └── js/
            └── bank_statement.js
```

## Troubleshooting

### Common Issues

1. **Tesseract not found**:
   - Install Tesseract: `brew install tesseract` (macOS) or `apt-get install tesseract-ocr` (Ubuntu)
   - Update `TESSERACT_CMD` in settings

2. **PDF processing errors**:
   - Install poppler: `brew install poppler` (macOS) or `apt-get install poppler-utils` (Ubuntu)

3. **Redis connection errors**:
   - Start Redis server: `redis-server`
   - Check Redis URL in settings

4. **File upload issues**:
   - Check file size limits in settings
   - Verify media directory permissions

5. **OCR accuracy issues**:
   - Ensure high-quality images
   - Try different OCR engines (Tesseract vs PaddleOCR)
   - Preprocess images for better results

### Logging

Check logs for detailed error information:

```python
# In Django shell
from bank_statement.models import ProcessingLog
logs = ProcessingLog.objects.filter(status='failed').order_by('-created_at')
for log in logs:
    print(f"{log.created_at}: {log.error_message}")
```

## Performance Optimization

### Database
- Use database indexes on frequently queried fields
- Implement pagination for large datasets
- Use select_related() for foreign key queries

### File Processing
- Process files asynchronously with Celery
- Implement file compression for storage
- Cache processed results

### Frontend
- Use lazy loading for images
- Implement client-side pagination
- Minimize JavaScript bundle size

## Security Considerations

- File type validation
- File size limits
- CSRF protection
- SQL injection prevention
- XSS protection
- Secure file storage
- User authentication
- Permission-based access

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This bank statement processing system is part of the Django on Docker application and is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs
3. Create an issue with detailed information

## Changelog

### Version 1.0.0
- Initial release
- PDF and image processing
- Transaction management
- Export functionality
- Responsive UI
- Background processing