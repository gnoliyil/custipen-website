import os

class AppConfig:
    PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
    DATABASE = '/var/www/custipen-website/users.db' 
    SECRET_KEY = 'development key'
    USERNAME = 'admin'
    PASSWORD = 'default'
    UPLOAD_FOLDER = './uploads/'
    MAX_CONTENT_LENGTH = 7 * 1024 * 1024
    MEDIA_FOLDER = 'images'
