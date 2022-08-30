import base64
import uuid

import boto3
from boto3 import s3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from odoo import models, api
import logging


class S3Attachment(models.Model):
    _inherit = 'ir.attachment'

