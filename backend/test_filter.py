import sys; sys.path.insert(0, '.')
from workers.crawl_worker import _is_valid_tender_item, _score_tender

tests = [
    ('3D Concrete Printing Pilot Project', 'http://x.com/tender/123', True),
    ('Additive Manufacturing Construction Contract', 'http://x.com/t/1', True),
    ('Road Repair Desilting Work', 'http://x.com/t/2', False),
    ('Civil Infrastructure Maintenance', 'http://x.com/t/3', False),
    ('HVAC Building Maintenance', 'http://x.com/t/4', False),
    ('Robotic Construction 3D Printing Lab', 'http://x.com/t/5', True),
]
all_ok = True
for title, url, expected in tests:
    result = _is_valid_tender_item(title, url)
    ok = result == expected
    all_ok = all_ok and ok
    status = "OK" if ok else "FAIL"
    print(f"{status} | {title[:50]} -> {result} (expected {expected})")

score, decision = _score_tender("3D Concrete Printing Pilot Project")
print(f"Score: {score}, Decision: {decision}")
print("All filter tests OK:", all_ok)
