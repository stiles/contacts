#!/usr/bin/env python3
"""
Contact Merger - Sync and clean up contacts from Google and iOS

This script helps you:
1. Import contacts from Google Contacts and/or iCloud exports
2. Detect duplicate contacts
3. Find contacts missing from your iPhone
4. Generate clean vCard files for import

Usage:
    python merge_contacts.py --google google_contacts.vcf
    python merge_contacts.py --google google_contacts.vcf --ios iphone_contacts.vcf
"""

import argparse
import os
import sys
from datetime import datetime

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'lib'))

from vcard_parser import parse_vcard_file, export_contacts_to_vcard, Contact
from detect_duplicates import (
    find_duplicates, 
    find_missing_contacts, 
    merge_duplicate_contacts
)


def generate_duplicate_report(duplicates, output_path="duplicate_report.txt"):
    """Generate a human-readable duplicate report."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"Duplicate Contact Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total duplicate pairs found: {len(duplicates)}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, (contact1, contact2, reason) in enumerate(duplicates, 1):
            f.write(f"Duplicate #{i}\n")
            f.write(f"Reason: {reason}\n")
            f.write(f"\nContact A:\n")
            f.write(f"  Name: {contact1.full_name}\n")
            f.write(f"  Phones: {', '.join(contact1.phones) if contact1.phones else 'None'}\n")
            f.write(f"  Emails: {', '.join(contact1.emails) if contact1.emails else 'None'}\n")
            f.write(f"  Organization: {contact1.organization or 'None'}\n")
            
            f.write(f"\nContact B:\n")
            f.write(f"  Name: {contact2.full_name}\n")
            f.write(f"  Phones: {', '.join(contact2.phones) if contact2.phones else 'None'}\n")
            f.write(f"  Emails: {', '.join(contact2.emails) if contact2.emails else 'None'}\n")
            f.write(f"  Organization: {contact2.organization or 'None'}\n")
            f.write("\n" + "-" * 80 + "\n\n")
    
    print(f"✓ Duplicate report saved to: {output_path}")


def generate_missing_report(missing_contacts, output_path="missing_contacts_report.txt"):
    """Generate a report of contacts missing from iPhone."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"Missing Contacts Report\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total contacts missing from iPhone: {len(missing_contacts)}\n")
        f.write("=" * 80 + "\n\n")
        
        for i, contact in enumerate(missing_contacts, 1):
            f.write(f"{i}. {contact.full_name}\n")
            if contact.phones:
                f.write(f"   Phones: {', '.join(contact.phones)}\n")
            if contact.emails:
                f.write(f"   Emails: {', '.join(contact.emails)}\n")
            if contact.organization:
                f.write(f"   Organization: {contact.organization}\n")
            f.write("\n")
    
    print(f"✓ Missing contacts report saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Sync and clean up contacts from Google and iOS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check Google contacts for duplicates only
  python merge_contacts.py --google data/input/google_contacts.vcf
  
  # Find what's missing from iPhone
  python merge_contacts.py --google data/input/google_contacts.vcf --ios data/input/icloud_contacts.vcf
  
  # Custom output directory
  python merge_contacts.py --google data/input/google_contacts.vcf --output-dir output/
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
        default=0.85,
        help='Name similarity threshold for duplicate detection (0.0-1.0, default: 0.85)'
    )
    
    args = parser.parse_args()
    
    # Create output directory if needed
    if args.output_dir != '.' and not os.path.exists(args.output_dir):
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
    
    # Detect duplicates in Google contacts
    print(f"\nDetecting duplicates in Google contacts...")
    google_duplicates = find_duplicates(google_contacts, name_threshold=args.name_threshold)
    print(f"✓ Found {len(google_duplicates)} potential duplicate pairs")
    
    if google_duplicates:
        report_path = os.path.join(args.output_dir, "google_duplicates_report.txt")
        generate_duplicate_report(google_duplicates, report_path)
    
    # If iOS contacts provided, find what's missing
    if ios_contacts:
        print(f"\nFinding contacts missing from iPhone...")
        missing = find_missing_contacts(google_contacts, ios_contacts)
        print(f"✓ Found {len(missing)} contacts in Google that aren't on iPhone")
        
        if missing:
            # Generate report
            report_path = os.path.join(args.output_dir, "missing_contacts_report.txt")
            generate_missing_report(missing, report_path)
            
            # Export missing contacts to vCard
            vcard_path = os.path.join(args.output_dir, "missing_contacts.vcf")
            export_contacts_to_vcard(missing, vcard_path)
            print(f"✓ Missing contacts exported to: {vcard_path}")
            print(f"\n  → You can import this file to your iPhone via:")
            print(f"     • Email it to yourself and open on iPhone")
            print(f"     • AirDrop to iPhone")
            print(f"     • Upload to iCloud.com (Contacts → Settings gear → Import vCard)")
        
        # Check for duplicates across both sources
        print(f"\nDetecting duplicates across Google and iOS contacts...")
        all_contacts = google_contacts + ios_contacts
        cross_duplicates = find_duplicates(all_contacts, name_threshold=args.name_threshold)
        
        # Filter to only cross-platform duplicates
        cross_only = []
        for contact1, contact2, reason in cross_duplicates:
            if (contact1 in google_contacts and contact2 in ios_contacts) or \
               (contact2 in google_contacts and contact1 in ios_contacts):
                cross_only.append((contact1, contact2, reason))
        
        if cross_only:
            print(f"✓ Found {len(cross_only)} duplicates across platforms")
            report_path = os.path.join(args.output_dir, "cross_platform_duplicates.txt")
            generate_duplicate_report(cross_only, report_path)
    
    # Generate cleaned contacts file (all unique Google contacts)
    print(f"\nGenerating cleaned contacts file...")
    
    # Create a set to track which contacts are duplicates
    duplicate_indices = set()
    for contact1, contact2, _ in google_duplicates:
        # Find indices
        try:
            idx1 = google_contacts.index(contact1)
            idx2 = google_contacts.index(contact2)
            duplicate_indices.add(max(idx1, idx2))  # Keep first, mark second as duplicate
        except ValueError:
            pass
    
    # Keep only non-duplicate contacts
    unique_contacts = [c for i, c in enumerate(google_contacts) if i not in duplicate_indices]
    
    cleaned_path = os.path.join(args.output_dir, "cleaned_google_contacts.vcf")
    export_contacts_to_vcard(unique_contacts, cleaned_path)
    print(f"✓ Cleaned contacts exported to: {cleaned_path}")
    print(f"  (Removed {len(duplicate_indices)} duplicates, kept {len(unique_contacts)} unique contacts)")
    
    print("\n" + "=" * 80)
    print("Summary:")
    print(f"  • Google contacts: {len(google_contacts)}")
    if ios_contacts:
        print(f"  • iOS contacts: {len(ios_contacts)}")
        print(f"  • Missing from iPhone: {len(missing)}")
    print(f"  • Duplicates found: {len(google_duplicates)} pairs")
    print(f"  • Unique contacts: {len(unique_contacts)}")
    print("\nNext steps:")
    if ios_contacts and missing:
        print(f"  1. Review {os.path.join(args.output_dir, 'missing_contacts_report.txt')}")
        print(f"  2. Import {os.path.join(args.output_dir, 'missing_contacts.vcf')} to iPhone")
    if google_duplicates:
        print(f"  3. Review {os.path.join(args.output_dir, 'google_duplicates_report.txt')}")
        print(f"  4. Clean up duplicates in Google Contacts manually if needed")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
