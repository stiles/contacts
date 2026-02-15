#!/usr/bin/env python3
"""
Create Master Contacts - Automatically merge and deduplicate all contacts

This script combines contacts from Google and iOS, automatically merges duplicates,
and creates a single master contacts file ready for import.

Usage:
    python create_master_contacts.py --google data/input/google_contacts.vcf
    python create_master_contacts.py --google data/input/google_contacts.vcf --ios data/input/icloud_contacts.vcf
"""

import argparse
import os
import sys
from datetime import datetime
import vobject

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from vcard_parser import parse_vcard_file, Contact
from detect_duplicates import find_duplicates


def create_merged_vcard(contact: Contact) -> vobject.vCard:
    """Create a new vCard object from a Contact."""
    vcard = vobject.vCard()
    
    # Full name (required by vCard standard)
    full_name = contact.full_name
    if not full_name:
        # Generate from first/last name
        if contact.first_name or contact.last_name:
            full_name = f"{contact.first_name} {contact.last_name}".strip()
        # Use phone or email as fallback
        elif contact.phones:
            full_name = contact.phones[0]
        elif contact.emails:
            full_name = contact.emails[0]
        # Last resort - use organization or placeholder
        elif contact.organization:
            full_name = str(contact.organization)
        else:
            full_name = "Unknown Contact"
    
    vcard.add('fn')
    vcard.fn.value = full_name
    
    # Structured name
    vcard.add('n')
    vcard.n.value = vobject.vcard.Name(
        family=contact.last_name or '',
        given=contact.first_name or ''
    )
    
    # Phone numbers
    for phone in contact.phones:
        if phone:  # Skip empty phone numbers
            tel = vcard.add('tel')
            tel.value = phone
            tel.type_param = 'CELL'
    
    # Emails
    for email in contact.emails:
        if email:  # Skip empty emails
            email_entry = vcard.add('email')
            email_entry.value = email
            email_entry.type_param = 'INTERNET'
    
    # Organization
    if contact.organization:
        org = vcard.add('org')
        # ORG should be a list in vCard format
        if isinstance(contact.organization, list):
            org.value = contact.organization
        else:
            org.value = [contact.organization]
    
    # Note
    if contact.note:
        vcard.add('note')
        vcard.note.value = contact.note
    
    # Addresses
    for addr in contact.addresses:
        try:
            vcard.add('adr').value = addr.value
        except:
            pass  # Skip if address can't be added
    
    # Photo
    if contact.photo:
        try:
            vcard.add('photo')
            vcard.photo = contact.photo
        except:
            pass  # Skip if photo can't be added
    
    return vcard


def merge_two_contacts(contact1: Contact, contact2: Contact) -> Contact:
    """
    Merge two contacts into one, combining all information.
    """
    merged = Contact()
    
    # Use the longer/more complete name
    if len(contact1.full_name) >= len(contact2.full_name):
        merged.full_name = contact1.full_name
        merged.first_name = contact1.first_name or contact2.first_name
        merged.last_name = contact1.last_name or contact2.last_name
    else:
        merged.full_name = contact2.full_name
        merged.first_name = contact2.first_name or contact1.first_name
        merged.last_name = contact2.last_name or contact1.last_name
    
    # Combine and deduplicate phones
    all_phones = contact1.phones + contact2.phones
    seen_normalized = set()
    unique_phones = []
    for phone in all_phones:
        normalized = contact1.normalize_phone(phone)
        if normalized and normalized not in seen_normalized:
            seen_normalized.add(normalized)
            unique_phones.append(phone)
    merged.phones = unique_phones
    
    # Combine and deduplicate emails (case-insensitive)
    seen_emails = set()
    unique_emails = []
    for email in contact1.emails + contact2.emails:
        email_lower = email.lower()
        if email_lower not in seen_emails:
            seen_emails.add(email_lower)
            unique_emails.append(email)
    merged.emails = unique_emails
    
    # Use non-empty organization (prefer contact1 if both have one)
    org1 = contact1.organization
    org2 = contact2.organization
    if org1 and org2:
        # If both have organizations, prefer the longer/more detailed one
        merged.organization = org1 if len(str(org1)) >= len(str(org2)) else org2
    else:
        merged.organization = org1 or org2
    
    # Merge notes
    notes = []
    if contact1.note:
        notes.append(contact1.note)
    if contact2.note and contact2.note != contact1.note:
        notes.append(contact2.note)
    merged.note = '\n---\n'.join(notes) if notes else ""
    
    # Keep photo if either has one (prefer contact1)
    merged.photo = contact1.photo or contact2.photo
    
    # Combine addresses (deduplicate by string representation)
    seen_addresses = set()
    unique_addresses = []
    for addr in contact1.addresses + contact2.addresses:
        addr_str = str(addr.value) if hasattr(addr, 'value') else str(addr)
        if addr_str not in seen_addresses:
            seen_addresses.add(addr_str)
            unique_addresses.append(addr)
    merged.addresses = unique_addresses
    
    return merged


def auto_merge_duplicates(contacts: list, name_threshold: float = 0.90) -> tuple[list, list]:
    """
    Automatically merge duplicate contacts.
    
    Returns:
        Tuple of (merged_contacts, merge_log)
    """
    # Find all duplicates
    duplicates = find_duplicates(contacts, name_threshold=name_threshold)
    
    # Build a map of which contacts should be merged together
    # Use union-find structure to group all related contacts
    contact_to_group = {}
    groups = []
    
    def find_group(contact):
        """Find which group a contact belongs to."""
        for i, group in enumerate(groups):
            if contact in group:
                return i
        return None
    
    def merge_groups(group1_idx, group2_idx):
        """Merge two groups together."""
        if group1_idx == group2_idx:
            return
        groups[group1_idx].update(groups[group2_idx])
        groups[group2_idx] = set()  # Empty the merged group
    
    # Build groups of contacts that should be merged
    for contact1, contact2, reason in duplicates:
        group1 = find_group(contact1)
        group2 = find_group(contact2)
        
        if group1 is None and group2 is None:
            # Create new group
            groups.append({contact1, contact2})
        elif group1 is None:
            # Add contact1 to group2
            groups[group2].add(contact1)
        elif group2 is None:
            # Add contact2 to group1
            groups[group1].add(contact2)
        else:
            # Merge the two groups
            merge_groups(group1, group2)
    
    # Remove empty groups
    groups = [g for g in groups if g]
    
    # Track which contacts have been merged
    merged_contacts_set = set()
    for group in groups:
        merged_contacts_set.update(group)
    
    # Merge each group
    merged_results = []
    merge_log = []
    
    for group in groups:
        group_list = list(group)
        # Start with first contact and merge in all others
        result = group_list[0]
        contact_names = [result.full_name]
        
        for contact in group_list[1:]:
            result = merge_two_contacts(result, contact)
            contact_names.append(contact.full_name)
        
        merged_results.append(result)
        merge_log.append(f"Merged {len(group)} contacts: {' + '.join(contact_names)} -> {result.full_name}")
    
    # Add contacts that weren't duplicates
    for contact in contacts:
        if contact not in merged_contacts_set:
            merged_results.append(contact)
    
    return merged_results, merge_log


def main():
    parser = argparse.ArgumentParser(
        description="Automatically merge and deduplicate contacts to create a master file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Merge Google contacts only
  python create_master_contacts.py --google data/input/google_contacts.vcf
  
  # Merge both Google and iOS contacts
  python create_master_contacts.py --google data/input/google_contacts.vcf --ios data/input/icloud_contacts.vcf
        """
    )
    
    parser.add_argument(
        '--google',
        required=True,
        help='Path to Google Contacts vCard export file'
    )
    
    parser.add_argument(
        '--ios',
        help='Path to iOS/iCloud contacts vCard export file (optional)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='data/output',
        help='Directory for output files (default: data/output/)'
    )
    
    parser.add_argument(
        '--name-threshold',
        type=float,
        default=0.90,
        help='Name similarity threshold for merging (0.0-1.0, default: 0.90)'
    )
    
    args = parser.parse_args()
    
    # Create output directory if needed
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Parse Google contacts
    print(f"\nParsing Google contacts from: {args.google}")
    google_contacts = parse_vcard_file(args.google)
    print(f"✓ Found {len(google_contacts)} Google contacts")
    
    # Parse iOS contacts if provided
    ios_contacts = []
    if args.ios:
        print(f"\nParsing iOS contacts from: {args.ios}")
        ios_contacts = parse_vcard_file(args.ios)
        print(f"✓ Found {len(ios_contacts)} iOS contacts")
    
    # Combine all contacts
    all_contacts = google_contacts + ios_contacts
    print(f"\nTotal contacts before merging: {len(all_contacts)}")
    
    # Auto-merge duplicates
    print(f"\nMerging duplicates (name threshold: {args.name_threshold})...")
    merged_contacts, merge_log = auto_merge_duplicates(all_contacts, name_threshold=args.name_threshold)
    
    print(f"✓ Merged into {len(merged_contacts)} unique contacts")
    print(f"✓ Performed {len(merge_log)} merge operations")
    
    # Save merge log
    log_path = os.path.join(args.output_dir, "merge_log.txt")
    with open(log_path, 'w', encoding='utf-8') as f:
        f.write(f"Contact Merge Log\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total contacts before: {len(all_contacts)}\n")
        f.write(f"Total contacts after: {len(merged_contacts)}\n")
        f.write(f"Merge operations: {len(merge_log)}\n")
        f.write("=" * 80 + "\n\n")
        
        for log_entry in merge_log:
            f.write(log_entry + "\n")
    
    print(f"✓ Merge log saved to: {log_path}")
    
    # Create master contacts vCard file
    print(f"\nGenerating master contacts file...")
    master_path = os.path.join(args.output_dir, "master_contacts.vcf")
    
    with open(master_path, 'w', encoding='utf-8') as f:
        for contact in merged_contacts:
            # Create a new vCard for this contact
            vcard = create_merged_vcard(contact)
            f.write(vcard.serialize())
    
    print(f"✓ Master contacts saved to: {master_path}")
    
    # Generate summary report
    summary_path = os.path.join(args.output_dir, "master_contacts_summary.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"Master Contacts Summary\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Source: Google Contacts\n")
        f.write(f"  • Original count: {len(google_contacts)}\n")
        if ios_contacts:
            f.write(f"\nSource: iOS/iCloud Contacts\n")
            f.write(f"  • Original count: {len(ios_contacts)}\n")
        f.write(f"\nResults:\n")
        f.write(f"  • Total contacts before merge: {len(all_contacts)}\n")
        f.write(f"  • Duplicates merged: {len(all_contacts) - len(merged_contacts)}\n")
        f.write(f"  • Final contact count: {len(merged_contacts)}\n")
        f.write(f"\nOutput file: {master_path}\n")
        f.write(f"Merge log: {log_path}\n")
    
    print(f"✓ Summary saved to: {summary_path}")
    
    print("\n" + "=" * 80)
    print("Master Contacts Created Successfully!")
    print("=" * 80)
    print(f"  • Original contacts: {len(all_contacts)}")
    print(f"  • Merged duplicates: {len(all_contacts) - len(merged_contacts)}")
    print(f"  • Final unique contacts: {len(merged_contacts)}")
    print(f"\nMaster file: {master_path}")
    print(f"\nYou can now import this file to your iPhone via:")
    print(f"  • iCloud.com (Contacts → Settings → Import vCard)")
    print(f"  • Email the file to yourself")
    print(f"  • AirDrop to iPhone")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
