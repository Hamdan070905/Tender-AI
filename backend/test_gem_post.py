import asyncio, httpx, re

async def gem_csrf_post():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://bidplus.gem.gov.in/all-bids',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        r1 = await client.get('https://bidplus.gem.gov.in/all-bids')
        csrf_cookie = client.cookies.get('csrf_gem_cookie')
        
        m = re.search(r'csrf_bd_gem_nk.*?[\'"]([a-f0-9]{32})[\'"]', r1.text)
        token = m.group(1) if m else csrf_cookie
        print('Cookie:', csrf_cookie)
        print('Token found:', token)
        
        data = {
            'payload': '{"searchBid":"","filter":{"bidStatusType":"ongoing_bids"}}',
            'csrf_bd_gem_nk': token
        }
        r2 = await client.post('https://bidplus.gem.gov.in/all-bids-data', data=data)
        print('POST status:', r2.status_code, 'Content-Type:', r2.headers.get('content-type'))
        print('Snippet:', r2.text[:400])

if __name__ == '__main__':
    asyncio.run(gem_csrf_post())
