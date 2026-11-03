# Minimal client for Bungie's Destiny 2 REST API: sends the API key with every
# request, keeps to RATE requests a second across threads, retries throttling,
# server errors and dropped connections, and raises BungieError on Bungie's
# other errors. Every endpoint used is public, so there is no OAuth.
import threading
import time

import requests

RATE = 20  # requests a second, across threads
RETRIES = 3
# ErrorCodes for Bungie's throttles (ThrottleLimitExceeded and its kin, and
# DestinyThrottledByGameServer): retried after ThrottleSeconds.
THROTTLED = {31, 35, 36, 37, 51, 54, 55, 56, 57, 1672}
# SystemDisabled: the API is down for maintenance.
SYSTEM_DISABLED = 5


class BungieError(Exception):
    # An error Bungie answered with, with its ErrorCode as code.
    def __init__(self, code: int, message: str):
        super().__init__(f"{message} (ErrorCode {code})")
        self.code = code


class BungieAPI:
    # Requests share one session, which carries the API key, and one pace.

    BASE_URL = "https://www.bungie.net/Platform"
    # Carnage reports are served from their own host.
    STATS_URL = "https://stats.bungie.net/Platform"

    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers['X-API-Key'] = api_key
        self.lock = threading.Lock()
        self.next_at = 0.0

    def wait_turn(self) -> None:
        # Sleep until this request keeps the pace at RATE a second.
        # ponytail: one pace for the whole key; per-endpoint pacing if Bungie throttles us anyway
        with self.lock:
            now = time.monotonic()
            at = max(now, self.next_at)
            self.next_at = at + 1 / RATE
        time.sleep(at - now)

    def request(self, method: str, url: str, **kwargs):
        # The 'Response' part of a Bungie reply. Throttles wait ThrottleSeconds
        # (at least 1, 2, then 4 s) and retry, as do HTTP 5xx replies without
        # a Bungie error and dropped connections; Bungie's other errors, and
        # replies with no error code, raise BungieError.
        for attempt in range(RETRIES + 1):
            last = attempt == RETRIES
            self.wait_turn()
            try:
                response = self.session.request(method, url, timeout=30, **kwargs)
            except (requests.ConnectionError, requests.Timeout):
                if last:
                    raise
                time.sleep(2**attempt)
                continue
            try:
                data = response.json()
            except ValueError:
                data = {}
            code = data.get('ErrorCode')
            if code == 1:
                return data['Response']
            if code in THROTTLED and not last:
                time.sleep(max(data.get('ThrottleSeconds') or 0, 2**attempt))
                continue
            if code is not None:
                raise BungieError(code, data.get('Message'))
            # A server error that outlasts the retries stops the run.
            if response.status_code >= 500:
                if not last:
                    time.sleep(2**attempt)
                    continue
                response.raise_for_status()
            raise BungieError(0, f"HTTP {response.status_code} without a Bungie error code")

    def api_get(self, endpoint: str, params: dict | None = None, base: str = BASE_URL):
        # GET a Platform endpoint (e.g. "/Destiny2/Manifest/") and return the
        # 'Response' part.
        return self.request('GET', f"{base}{endpoint}", params=params)

    def get_manifest(self) -> dict:
        # Current manifest metadata, including the database download paths.
        return self.api_get("/Destiny2/Manifest/")

    def get_memberships(self, membership_id: str) -> dict:
        # The Destiny memberships of an account, by any of its membership ids,
        # under 'destinyMemberships' (each with membershipType and any
        # crossSaveOverride).
        return self.api_get(f"/User/GetMembershipsById/{membership_id}/-1/")

    def get_profile(self, membership_type: int, membership_id: str, components: list) -> dict:
        # A player's profile with the given components (DestinyComponentType:
        # 100 Profiles, 205 CharacterEquipment, 305 ItemSockets, ...).
        # membership_type is the platform: 1 Xbox, 2 PSN, 3 Steam, and so on.
        endpoint = f"/Destiny2/{membership_type}/Profile/{membership_id}/"
        return self.api_get(endpoint, {"components": ",".join(str(c) for c in components)})

    def get_activity_history(
        self,
        membership_type: int,
        membership_id: str,
        character_id: str,
        count: int = 1,
        mode: int | None = None,
        page: int = 0,
    ) -> dict:
        # A page of a character's activities, newest first, under 'activities'
        # (absent when there are none): count of them (250 at most), all modes
        # or one (DestinyActivityModeType, such as 4 Raid).
        endpoint = (
            f"/Destiny2/{membership_type}/Account/{membership_id}"
            f"/Character/{character_id}/Stats/Activities/"
        )
        params = {"count": count, "page": page}
        if mode:
            params["mode"] = mode
        return self.api_get(endpoint, params)

    def get_pgcr(self, instance_id: int) -> dict:
        # The post-game carnage report of one activity. A missing one raises
        # BungieError 1653 (DestinyPGCRNotFound): an id past the newest, an
        # activity still in progress, or a gap.
        return self.api_get(
            f"/Destiny2/Stats/PostGameCarnageReport/{instance_id}/", base=self.STATS_URL
        )
