import os
import sys
from pathlib import Path
import logging
import argparse

# Configure logging to match the main application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_wechat_parser")

# Add parent directory to path to import project modules
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix: Change from NeuroFeed.core to core since we already added the parent directory to path
from core.rss_parser import RssParser

class FileBasedResponse:
    """Mocks a Response object from requests for local file testing"""
    def __init__(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            self.text = f.read()
        self.encoding = 'utf-8'
        
    def __str__(self):
        return f"Response <{len(self.text)} bytes>"

def test_parser(file_path, real_network=False):
    """Test the parser on a specific file"""
    parser = RssParser()
    file_name = Path(file_path).name
    
    print(f"\n{'='*60}")
    print(f"Testing file: {file_path}")
    print(f"File type: {'ATOM' if file_name.endswith('.atom') else 'RSS'}")
    print(f"Using: {'Real network request' if real_network else 'Local file content'}")
    print(f"{'='*60}")
    
    if real_network:
        # Use the real URL (only works if you have a local server serving these files)
        url = f"http://localhost:4000/feeds/{file_name}"
        result = parser.fetch_feed(url)
    else:
        # Use mocking to avoid network requests
        original_get = parser.session.get
        try:
            # Replace the session.get with a function that returns file content
            def mock_get(url, **kwargs):
                logger.info(f"Mock request for URL: {url}")
                return FileBasedResponse(file_path)
                
            parser.session.get = mock_get
            
            # Call the parser with a fake URL that includes correct file extension
            fake_url = f"http://localhost:4000/feeds/{file_name}"
            result = parser.fetch_feed(fake_url)
        finally:
            # Restore original network function
            parser.session.get = original_get
    
    # Display results
    print("\nParsing Results:")
    print(f"Status: {result['status']}")
    
    if result['status'] == 'fail':
        print(f"Error: {result.get('error', 'Unknown error')}")
        return
        
    items = result.get('items', [])
    print(f"Number of items found: {len(items)}")
    
    for i, item in enumerate(items):
        print(f"\nItem #{i+1}:")
        print(f"  Title: {item.get('title', 'N/A')}")
        print(f"  Source: {item.get('source', 'N/A')}")
        
        content = item.get('content', '')
        content_length = len(content)
        print(f"  Content length: {content_length} characters")
        
        if content_length > 0:
            # Show first 100 chars of content as preview
            preview = content[:100] + "..." if content_length > 100 else content
            print(f"  Content preview: {preview}")
    
    return result

def main():
    """Main test function that runs tests on both file types"""
    parser = argparse.ArgumentParser(description='Test the WeChat RSS/ATOM parser')
    parser.add_argument('--network', action='store_true', help='Use actual network requests instead of file mocking')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get paths to test files
    test_dir = Path(__file__).parent
    atom_file = test_dir / "MP_WXS_2391738840.atom"
    rss_file = test_dir / "MP_WXS_2391738840.rss"
    
    # Verify files exist
    if not atom_file.exists():
        print(f"ATOM test file not found: {atom_file}")
    if not rss_file.exists():
        print(f"RSS test file not found: {rss_file}")
    
    # Test both file types
    if atom_file.exists():
        atom_result = test_parser(atom_file, args.network)
        
    if rss_file.exists():
        rss_result = test_parser(rss_file, args.network)
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary:")
    print(f"{'='*60}")
    
    if atom_file.exists() and rss_file.exists():
        # Compare content extraction effectiveness
        atom_content_len = len(atom_result['items'][0].get('content', '')) if atom_result.get('items') else 0
        rss_content_len = len(rss_result['items'][0].get('content', '')) if rss_result.get('items') else 0
        
        print(f"ATOM extraction: {'SUCCESS' if atom_content_len > 100 else 'PARTIAL' if atom_content_len > 0 else 'FAILED'}")
        print(f"RSS extraction: {'SUCCESS' if rss_content_len > 100 else 'PARTIAL' if rss_content_len > 0 else 'FAILED'}")
        
        if atom_result.get('items') and rss_result.get('items'):
            # Show which format provided more content
            if atom_content_len > rss_content_len:
                print(f"ATOM format provided more content ({atom_content_len} vs {rss_content_len} chars)")
            elif rss_content_len > atom_content_len:
                print(f"RSS format provided more content ({rss_content_len} vs {atom_content_len} chars)")
            else:
                print(f"Both formats provided same amount of content ({atom_content_len} chars)")

if __name__ == "__main__":
    main()
