from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from .models import FileUpload


class FileUploadTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a test file upload
        self.file_upload = FileUpload.objects.create(
            user=self.user,
            title='Test File',
            description='Test Description',
            file='test_files/test.txt'
        )
        
    def test_file_list_view(self):
        # Login the user
        self.client.login(username='testuser', password='testpassword')
        
        # Get the file list page
        response = self.client.get(reverse('file_list'))
        
        # Check that the response is 200 OK
        self.assertEqual(response.status_code, 200)
        
        # Check that the file is in the context
        self.assertContains(response, 'Test File')
    
    def test_file_upload_view(self):
        # Login the user
        self.client.login(username='testuser', password='testpassword')
        
        # Create a test file
        test_file = SimpleUploadedFile(
            name='test.txt',
            content=b'Test file content',
            content_type='text/plain'
        )
        
        # Post to the upload view
        response = self.client.post(
            reverse('upload_file'),
            {
                'title': 'Uploaded Test File',
                'description': 'Uploaded Test Description',
                'file': test_file
            },
            follow=True
        )
        
        # Check that the file was created
        self.assertTrue(FileUpload.objects.filter(title='Uploaded Test File').exists())
        
        # Check that we were redirected to the file list
        self.assertRedirects(response, reverse('file_list'))
