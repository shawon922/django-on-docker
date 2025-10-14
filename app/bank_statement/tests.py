from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import Statement, Transaction, ProcessingLog


class StatementModelTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a test statement
        self.statement = Statement.objects.create(
            user=self.user,
            title='Test Statement',
            file='test_statements/test.pdf',
            status='processed'
        )
    
    def test_statement_creation(self):
        self.assertEqual(self.statement.title, 'Test Statement')
        self.assertEqual(self.statement.user, self.user)
        self.assertEqual(self.statement.status, 'processed')


class TransactionModelTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a test statement
        self.statement = Statement.objects.create(
            user=self.user,
            title='Test Statement',
            file='test_statements/test.pdf',
            status='processed'
        )
        
        # Create a test transaction
        self.transaction = Transaction.objects.create(
            statement=self.statement,
            date='2023-01-01',
            description='Test Transaction',
            amount='100.00',
            transaction_type='debit'
        )
    
    def test_transaction_creation(self):
        self.assertEqual(self.transaction.description, 'Test Transaction')
        self.assertEqual(self.transaction.amount, '100.00')
        self.assertEqual(self.transaction.transaction_type, 'debit')
        self.assertEqual(self.transaction.statement, self.statement)


class StatementUploadViewTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Login the user
        self.client.login(username='testuser', password='testpassword')
        
        # URL for statement upload
        self.upload_url = reverse('statement_upload')
    
    def test_statement_upload_view_get(self):
        response = self.client.get(self.upload_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'bank_statement/upload.html')
