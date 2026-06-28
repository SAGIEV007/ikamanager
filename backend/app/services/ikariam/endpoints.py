"""Ikariam API endpoints and constants."""

# Gameforge Lobby
LOBBY_BASE = "https://lobby.ikariam.gameforge.com"
LOBBY_LOGIN = f"{LOBBY_BASE}/api/users"
LOBBY_ACCOUNTS = f"{LOBBY_BASE}/api/users/me/accounts"
LOBBY_SERVERS = f"{LOBBY_BASE}/api/servers"
LOBBY_LOGIN_LINK = f"{LOBBY_BASE}/api/users/me/loginLink"

# Pixel Zirkus (cookie)
PIXELZIRKUS_URL = "https://pixelzirkus.gameforge.com/do/simple"

# Game server base (format with server domain)
GAME_BASE = "https://s{server_number}-{language}.ikariam.gameforge.com"

# Game actions
GAME_INDEX = "/index.php"

# Common action parameters
ACTION_PARAMS = {
    "city_view": {"view": "city"},
    "island_view": {"view": "island"},
    "research_view": {"view": "research"},
    "military_view": {"view": "military"},
    "marketplace_view": {"view": "branchOffice"},
    "piracy_view": {"view": "pirateFortress"},
    "account_view": {"view": "finances"},
}

# Headers that simulate a real browser
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,pt-BR;q=0.8,pt;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Ch-Ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
}

LOBBY_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://lobby.ikariam.gameforge.com",
    "Referer": "https://lobby.ikariam.gameforge.com/",
}
