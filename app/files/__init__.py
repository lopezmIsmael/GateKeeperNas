from flask import Blueprint

bp = Blueprint('files', __name__, url_prefix='/files')

from app.files import routes
from app.files import upload
