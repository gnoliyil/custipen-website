import os

class AppConfig:
    DATABASE = 'users.db'
    SECRET_KEY = 'development key'
    USERNAME = 'admin'
    PASSWORD = 'default'
    UPLOAD_FOLDER = './uploads/'
    MAX_CONTENT_LENGTH = 7 * 1024 * 1024
    MEDIA_FOLDER = 'images'