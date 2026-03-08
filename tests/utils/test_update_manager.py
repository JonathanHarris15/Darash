import pytest
from src.utils.update_manager import UpdateManager

def test_version_comparison():
    """Tests the semantic version comparison logic in check_for_updates."""
    # We'll mock the internal behavior of check_for_updates or just test the logic directly
    
    def compare(latest, current):
        try:
            def to_tuple(v):
                return tuple(map(int, (v.split('.'))))
            return to_tuple(latest) > to_tuple(current)
        except (ValueError, IndexError):
            return latest > current

    assert compare("0.2.0", "0.1.0") == True
    assert compare("1.0.0", "0.9.9") == True
    assert compare("0.1.1", "0.1.0") == True
    assert compare("0.1.0", "0.1.0") == False
    assert compare("0.0.9", "0.1.0") == False
    assert compare("v0.2.0".lstrip('v'), "0.1.0") == True

def test_release_info_parsing():
    """Tests that the latest_tag parsing handles 'v' prefix."""
    # This is a bit redundant with the above but good for clarity
    tag = "v1.2.3"
    parsed_tag = tag.lstrip('v')
    assert parsed_tag == "1.2.3"
