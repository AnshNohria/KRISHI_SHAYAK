"""
FPO (Farmer Producer Organization) package for Krishi Dhan Sahayak
"""

from .service import FPOService, FPO, get_fpo_registration_benefits, get_fpo_registration_process, get_government_schemes_for_fpos

__all__ = [
    'FPOService',
    'FPO',
    'get_fpo_registration_benefits',
    'get_fpo_registration_process',
    'get_government_schemes_for_fpos'
]
