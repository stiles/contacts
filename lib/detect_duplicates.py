"""
Duplicate detection logic for contacts.
"""

from typing import List, Tuple, Set
from difflib import SequenceMatcher
from vcard_parser import Contact


def similarity_ratio(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def find_duplicates(contacts: List[Contact], name_threshold: float = 0.85, 
                   phone_match: bool = True) -> List[Tuple[Contact, Contact, str]]:
    """
    Find potential duplicate contacts.
    
    Args:
        contacts: List of Contact objects to check
        name_threshold: Similarity threshold for name matching (0.0-1.0)
        phone_match: If True, also match on phone numbers
        
    Returns:
        List of tuples: (contact1, contact2, reason)
    """
    duplicates = []
    
    # Track already compared pairs to avoid duplicates
    compared = set()
    
    for i, contact1 in enumerate(contacts):
        for j, contact2 in enumerate(contacts[i+1:], start=i+1):
            if (i, j) in compared:
                continue
            
            compared.add((i, j))
            reasons = []
            
            # Check phone number matches
            phones1 = set(contact1.get_normalized_phones())
            phones2 = set(contact2.get_normalized_phones())
            
            if phones1 and phones2 and phones1.intersection(phones2):
                reasons.append(f"Same phone: {phones1.intersection(phones2)}")
            
            # Check name similarity
            name1 = contact1.get_normalized_name()
            name2 = contact2.get_normalized_name()
            
            if name1 and name2:
                similarity = similarity_ratio(name1, name2)
                if similarity >= name_threshold:
                    reasons.append(f"Similar names: {similarity:.0%} match")
            
            # Check exact email matches
            emails1 = set([e.lower() for e in contact1.emails])
            emails2 = set([e.lower() for e in contact2.emails])
            
            if emails1 and emails2 and emails1.intersection(emails2):
                reasons.append(f"Same email: {emails1.intersection(emails2)}")
            
            # If we found any reason, mark as duplicate
            if reasons:
                duplicates.append((contact1, contact2, " | ".join(reasons)))
    
    return duplicates


def find_missing_contacts(source_contacts: List[Contact], 
                         target_contacts: List[Contact]) -> List[Contact]:
    """
    Find contacts in source that are not in target.
    
    Args:
        source_contacts: Contacts from source (e.g., Google)
        target_contacts: Contacts from target (e.g., iPhone)
        
    Returns:
        List of contacts from source that don't exist in target
    """
    # Build sets of normalized identifiers from target
    target_phones = set()
    target_names = set()
    target_emails = set()
    
    for contact in target_contacts:
        target_phones.update(contact.get_normalized_phones())
        target_names.add(contact.get_normalized_name())
        target_emails.update([e.lower() for e in contact.emails])
    
    missing = []
    
    for contact in source_contacts:
        # Check if this contact exists in target by any identifier
        has_phone_match = any(phone in target_phones 
                             for phone in contact.get_normalized_phones())
        has_name_match = contact.get_normalized_name() in target_names
        has_email_match = any(email.lower() in target_emails 
                             for email in contact.emails)
        
        # If no match found, it's missing
        if not (has_phone_match or has_name_match or has_email_match):
            missing.append(contact)
    
    return missing


def merge_duplicate_contacts(contact1: Contact, contact2: Contact) -> Contact:
    """
    Merge two duplicate contacts, keeping all unique information.
    
    Args:
        contact1: First contact
        contact2: Second contact
        
    Returns:
        Merged Contact object
    """
    merged = Contact()
    
    # Use the longer/more complete name
    merged.full_name = contact1.full_name if len(contact1.full_name) > len(contact2.full_name) else contact2.full_name
    merged.first_name = contact1.first_name or contact2.first_name
    merged.last_name = contact1.last_name or contact2.last_name
    
    # Combine and deduplicate phones
    all_phones = contact1.phones + contact2.phones
    seen_normalized = set()
    unique_phones = []
    for phone in all_phones:
        normalized = contact1.normalize_phone(phone)
        if normalized not in seen_normalized:
            seen_normalized.add(normalized)
            unique_phones.append(phone)
    merged.phones = unique_phones
    
    # Combine and deduplicate emails
    merged.emails = list(set(contact1.emails + contact2.emails))
    
    # Combine other fields
    merged.organization = contact1.organization or contact2.organization
    
    # Merge notes
    notes = []
    if contact1.note:
        notes.append(contact1.note)
    if contact2.note and contact2.note != contact1.note:
        notes.append(contact2.note)
    merged.note = '\n---\n'.join(notes) if notes else ""
    
    # Keep photo if either has one (prefer contact1)
    merged.photo = contact1.photo or contact2.photo
    
    # Combine addresses
    merged.addresses = contact1.addresses + contact2.addresses
    
    # Keep the raw vcard from contact1 (we'll update it)
    merged.raw_vcard = contact1.raw_vcard
    
    return merged
