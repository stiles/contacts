#!/usr/bin/env python3
"""
Filter Master Contacts - Remove contacts based on custom rules

This script applies filters defined in data/filter_config.yaml to create
a filtered version of your master contacts file.

Usage:
    python filter_contacts.py --input data/output/master_contacts.vcf
"""

import argparse
import os
import sys
import re
from datetime import datetime
import yaml

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from vcard_parser import parse_vcard_file, export_contacts_to_vcard


def load_filter_config(config_path):
    """Load filter configuration from YAML file."""
    if not os.path.exists(config_path):
        print(f"Warning: Filter config not found at {config_path}")
        print("Using empty filter (no contacts will be excluded)")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f) or {}
    
    # Ensure all fields are lists (handle None from commented YAML)
    for key in ['exclude_email_domains', 'exclude_emails', 'exclude_organizations', 
                'exclude_phone_prefixes', 'exclude_name_patterns', 'keep_if_note_contains']:
        if config.get(key) is None:
            config[key] = []
    
    return config


def should_exclude_contact(contact, config):
    """
    Check if a contact should be excluded based on filter rules.
    
    Returns:
        (should_exclude, reason)
    """
    # Check for exception tags in notes first
    keep_phrases = config.get('keep_if_note_contains', [])
    if keep_phrases and contact.note:
        for phrase in keep_phrases:
            if phrase and phrase.lower() in contact.note.lower():
                return False, None  # Keep this contact regardless of other rules
    
    # Check email domains
    exclude_domains = config.get('exclude_email_domains', [])
    for email in contact.emails:
        for domain in exclude_domains:
            if domain and domain.lower() in email.lower():
                return True, f"Email domain: {domain}"
    
    # Check specific emails
    exclude_emails = config.get('exclude_emails', [])
    for email in contact.emails:
        for excluded in exclude_emails:
            if excluded and email.lower() == excluded.lower():
                return True, f"Email: {excluded}"
    
    # Check organizations
    exclude_orgs = config.get('exclude_organizations', [])
    if contact.organization:
        org_str = str(contact.organization).lower()
        for excluded_org in exclude_orgs:
            if excluded_org and excluded_org.lower() in org_str:
                return True, f"Organization: {excluded_org}"
    
    # Check phone prefixes
    exclude_prefixes = config.get('exclude_phone_prefixes', [])
    for phone in contact.phones:
        # Normalize phone for comparison
        normalized_phone = re.sub(r'[^\d+]', '', phone)
        for prefix in exclude_prefixes:
            if prefix:
                normalized_prefix = re.sub(r'[^\d+]', '', prefix)
                if normalized_phone.startswith(normalized_prefix):
                    return True, f"Phone prefix: {prefix}"
    
    # Check name patterns
    exclude_patterns = config.get('exclude_name_patterns', [])
    name = contact.full_name.lower() if contact.full_name else ""
    for pattern in exclude_patterns:
        if pattern and pattern.lower() in name:
            return True, f"Name pattern: {pattern}"
    
    return False, None


def filter_contacts(contacts, config):
    """
    Filter contacts based on configuration rules.
    
    Returns:
        (filtered_contacts, excluded_contacts, exclusion_reasons)
    """
    filtered = []
    excluded = []
    exclusion_reasons = []
    
    for contact in contacts:
        should_exclude, reason = should_exclude_contact(contact, config)
        
        if should_exclude:
            excluded.append(contact)
            exclusion_reasons.append(reason)
        else:
            filtered.append(contact)
    
    return filtered, excluded, exclusion_reasons


def main():
    parser = argparse.ArgumentParser(
        description="Filter contacts based on custom rules",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Filter master contacts using default config
  python filter_contacts.py --input data/output/master_contacts.vcf
  
  # Use custom filter config
  python filter_contacts.py --input data/output/master_contacts.vcf --config my_filters.yaml
        """
    )
    
    parser.add_argument(
        '--input',
        required=True,
        help='Path to input contacts file (usually master_contacts.vcf)'
    )
    
    parser.add_argument(
        '--config',
        default='data/filter_config.yaml',
        help='Path to filter configuration file (default: data/filter_config.yaml)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='data/output',
        help='Directory for output files (default: data/output/)'
    )
    
    args = parser.parse_args()
    
    # Create output directory if needed
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Load filter config
    print(f"\nLoading filter configuration from: {args.config}")
    config = load_filter_config(args.config)
    
    # Count active rules
    active_rules = sum([
        len(config.get('exclude_email_domains', [])),
        len(config.get('exclude_emails', [])),
        len(config.get('exclude_organizations', [])),
        len(config.get('exclude_phone_prefixes', [])),
        len(config.get('exclude_name_patterns', []))
    ])
    print(f"✓ Loaded {active_rules} active exclusion rules")
    
    # Parse input contacts
    print(f"\nParsing contacts from: {args.input}")
    contacts = parse_vcard_file(args.input)
    print(f"✓ Found {len(contacts)} contacts")
    
    # Apply filters
    print(f"\nApplying filters...")
    filtered_contacts, excluded_contacts, exclusion_reasons = filter_contacts(contacts, config)
    
    print(f"✓ Kept {len(filtered_contacts)} contacts")
    print(f"✓ Excluded {len(excluded_contacts)} contacts")
    
    if len(excluded_contacts) == 0:
        print("\n✓ No contacts were excluded. Your filtered file is the same as the input.")
        print("  Edit data/filter_config.yaml to add exclusion rules.")
        return
    
    # Export filtered contacts
    output_path = os.path.join(args.output_dir, "filtered_contacts.vcf")
    export_contacts_to_vcard(filtered_contacts, output_path)
    print(f"✓ Filtered contacts saved to: {output_path}")
    
    # Export excluded contacts (for review)
    excluded_path = os.path.join(args.output_dir, "excluded_contacts.vcf")
    export_contacts_to_vcard(excluded_contacts, excluded_path)
    print(f"✓ Excluded contacts saved to: {excluded_path}")
    
    # Generate detailed exclusion report
    report_path = os.path.join(args.output_dir, "exclusion_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"Contact Exclusion Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Input file: {args.input}\n")
        f.write(f"Filter config: {args.config}\n\n")
        f.write(f"Total contacts: {len(contacts)}\n")
        f.write(f"Kept: {len(filtered_contacts)}\n")
        f.write(f"Excluded: {len(excluded_contacts)}\n\n")
        f.write("Excluded contacts:\n")
        f.write("-" * 80 + "\n\n")
        
        for i, (contact, reason) in enumerate(zip(excluded_contacts, exclusion_reasons), 1):
            f.write(f"{i}. {contact.full_name}\n")
            f.write(f"   Reason: {reason}\n")
            if contact.emails:
                f.write(f"   Emails: {', '.join(contact.emails)}\n")
            if contact.phones:
                f.write(f"   Phones: {', '.join(contact.phones[:2])}\n")
            if contact.organization:
                f.write(f"   Organization: {contact.organization}\n")
            f.write("\n")
    
    print(f"✓ Exclusion report saved to: {report_path}")
    
    print("\n" + "=" * 80)
    print("Filtering Complete")
    print("=" * 80)
    print(f"  • Original contacts: {len(contacts)}")
    print(f"  • Filtered contacts: {len(filtered_contacts)}")
    print(f"  • Excluded contacts: {len(excluded_contacts)}")
    print(f"\nFiltered file: {output_path}")
    print(f"Excluded file: {excluded_path} (for review)")
    print(f"\nImport the filtered file to your iPhone to exclude unwanted contacts.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
