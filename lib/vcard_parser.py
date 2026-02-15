"""
Utility functions for parsing vCard files and extracting contact information.
"""

import vobject
import re
from typing import List, Dict, Optional


class Contact:
    """Represents a single contact with normalized data."""
    
    def __init__(self, vcard_obj=None):
        self.raw_vcard = vcard_obj
        self.full_name = ""
        self.first_name = ""
        self.last_name = ""
        self.phones = []
        self.emails = []
        self.organization = ""
        self.note = ""
        self.photo = None
        self.addresses = []
        
        if vcard_obj:
            self._parse_vcard(vcard_obj)
    
    def _parse_vcard(self, vcard_obj):
        """Extract relevant fields from vCard object."""
        # Name
        if hasattr(vcard_obj, 'fn'):
            self.full_name = vcard_obj.fn.value
        
        if hasattr(vcard_obj, 'n'):
            n = vcard_obj.n.value
            self.last_name = n.family if hasattr(n, 'family') else ""
            self.first_name = n.given if hasattr(n, 'given') else ""
        
        # Phone numbers
        if hasattr(vcard_obj, 'tel_list'):
            for tel in vcard_obj.tel_list:
                self.phones.append(tel.value)
        
        # Emails
        if hasattr(vcard_obj, 'email_list'):
            for email in vcard_obj.email_list:
                self.emails.append(email.value)
        
        # Organization
        if hasattr(vcard_obj, 'org'):
            org_value = vcard_obj.org.value
            # ORG is a list in vCard format, extract the first element (organization name)
            if isinstance(org_value, list):
                self.organization = org_value[0] if org_value else ""
            else:
                self.organization = str(org_value) if org_value else ""
        
        # Note
        if hasattr(vcard_obj, 'note'):
            self.note = vcard_obj.note.value
        
        # Photo
        if hasattr(vcard_obj, 'photo'):
            self.photo = vcard_obj.photo
        
        # Addresses
        if hasattr(vcard_obj, 'adr_list'):
            for adr in vcard_obj.adr_list:
                self.addresses.append(adr)
    
    def normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number for comparison.
        Removes all non-digit characters except +.
        """
        # Keep only digits and +
        normalized = re.sub(r'[^\d+]', '', phone)
        
        # Remove leading 1 for US numbers (if it's exactly 11 digits starting with 1)
        if len(normalized) == 11 and normalized.startswith('1'):
            normalized = normalized[1:]
        
        # Remove country code + if present
        if normalized.startswith('+'):
            # Remove + and country code (1-3 digits)
            normalized = re.sub(r'^\+\d{1,3}', '', normalized)
        
        return normalized
    
    def get_normalized_phones(self) -> List[str]:
        """Return list of normalized phone numbers."""
        return [self.normalize_phone(p) for p in self.phones if p]
    
    def get_normalized_name(self) -> str:
        """Return normalized name for comparison (lowercase, no extra spaces)."""
        name = self.full_name or f"{self.first_name} {self.last_name}".strip()
        return ' '.join(name.lower().split())
    
    def __repr__(self):
        phones_str = ', '.join(self.phones[:2]) if self.phones else 'No phone'
        emails_str = ', '.join(self.emails[:1]) if self.emails else 'No email'
        return f"Contact({self.full_name} | {phones_str} | {emails_str})"


def parse_vcard_file(filepath: str) -> List[Contact]:
    """
    Parse a vCard file and return a list of Contact objects.
    
    Args:
        filepath: Path to the .vcf or .vcard file
        
    Returns:
        List of Contact objects
    """
    contacts = []
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # vCard files can contain multiple contacts
        # Split by BEGIN:VCARD to handle multiple contacts
        vcard_strings = content.split('BEGIN:VCARD')
        
        for vcard_str in vcard_strings:
            if not vcard_str.strip():
                continue
            
            # Re-add BEGIN:VCARD
            vcard_str = 'BEGIN:VCARD' + vcard_str
            
            try:
                vcard_obj = vobject.readOne(vcard_str)
                contact = Contact(vcard_obj)
                contacts.append(contact)
            except Exception as e:
                print(f"Warning: Failed to parse a contact: {e}")
                continue
    
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return []
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return []
    
    return contacts


def export_contacts_to_vcard(contacts: List[Contact], output_path: str):
    """
    Export a list of Contact objects to a vCard file.
    
    Args:
        contacts: List of Contact objects
        output_path: Path where the .vcf file will be saved
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for contact in contacts:
            if contact.raw_vcard:
                f.write(contact.raw_vcard.serialize())
