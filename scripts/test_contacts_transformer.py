"""
Test the contacts transformer with real Wix API data.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from wix_api.client import WixAPIClient
from transformers.contacts import ContactsTransformer


def main():
    """Test the contacts transformer."""
    print("=" * 80)
    print("Testing Contacts Transformer")
    print("=" * 80)

    # Initialize API client
    print("\n1. Initializing Wix API client...")
    client = WixAPIClient.from_env()

    # Get contacts
    print("\n2. Fetching contacts from API...")
    query = {'paging': {'limit': 10}}
    response = client.post('/contacts/v4/contacts/query', json=query)
    contacts = response.get('contacts', [])
    print(f"   Retrieved {len(contacts)} contacts")

    if not contacts:
        print("No contacts found!")
        return

    # Show original format
    print("\n3. Original contact format (sample):")
    print("-" * 80)
    first_contact = contacts[0]
    print(f"  ID: {first_contact.get('id')}")
    print(f"  Email: {first_contact.get('primaryInfo', {}).get('email')}")
    print(f"  Name: {first_contact.get('info', {}).get('name', {})}")
    print(f"  Member: {'memberInfo' in first_contact}")

    # Transform contacts
    print("\n4. Transforming contacts...")
    transformed_contacts = ContactsTransformer.transform_contacts(contacts)

    # Show transformed format
    print("\n5. Transformed contact format (sample):")
    print("-" * 80)
    first_transformed = transformed_contacts[0]
    for key, value in first_transformed.items():
        if isinstance(value, str) and len(value) > 80:
            value = value[:80] + "..."
        print(f"  {key}: {value}")

    # Create DataFrame
    print("\n6. Creating DataFrame...")
    df = ContactsTransformer.to_dataframe(transformed_contacts)
    print(f"   DataFrame shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")

    # Show sample data
    print("\n7. Sample data (first row, key columns):")
    print("-" * 80)
    key_columns = ['full_name', 'email', 'is_member', 'member_status', 'created_date']
    available_columns = [col for col in key_columns if col in df.columns]
    if len(df) > 0:
        print(df[available_columns].head(1).to_string(index=False))

    # Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = project_root / "data" / "processed" / f"contacts_test_{timestamp}.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n8. Saving to CSV: {output_path}")
    ContactsTransformer.save_to_csv(contacts, str(output_path))
    print(f"   ✓ Saved successfully!")

    # Verify encoding
    with open(output_path, 'rb') as f:
        first_bytes = f.read(3)
        if first_bytes == b'\xef\xbb\xbf':
            print("   ✓ File has UTF-8 BOM (Excel-friendly)")

    print("\n" + "=" * 80)
    print("✓ Contacts transformer test completed successfully!")
    print("=" * 80)

    # Summary
    print("\nSummary:")
    print(f"  - Raw fields: Many nested objects")
    print(f"  - Transformed fields: {len(first_transformed)}")
    print(f"  - Records: {len(df)}")
    print(f"  - Output: {output_path.name}")


if __name__ == "__main__":
    main()
