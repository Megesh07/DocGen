"""Templates package."""
from autodocstring.generator.templates.base import BaseTemplate
from autodocstring.generator.templates.google import GoogleTemplate
from autodocstring.generator.templates.numpy import NumpyTemplate
from autodocstring.generator.templates.rest import RestTemplate

__all__ = [
    "BaseTemplate",
    "GoogleTemplate",
    "NumpyTemplate",
    "RestTemplate",
]
