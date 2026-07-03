import os, json, ssl, urllib.request, re
from datetime import datetime, date
from collections import Counter

ssl._create_default_https_context = ssl._create_unverified_context


# Zodiac reference data (self-contained, no circular import)
ZODIAC_MAP = ["鼠","牛","虎","兔","龍","蛇","馬","羊","猴","雞","狗","豬"]
_LUNAR_NEW_YEAR = {
    "2023-01-22": "兔", "2024-02-10": "龍",
    "2025-01-29": "蛇", "2026-02-17": "馬"
}

def _get_year_zodiac(date_str):
    if not date_str or len(date_str) < 10:
        return "馬"
    d = date_str[:10]
    zodiac = "馬"
    for dt, z in sorted(_LUNAR_NEW_YEAR.items()):
        if d >= dt:
            zodiac = z
    return zodiac

def _num_to_zodiac(num, date_str=None):
    n = int(num)
    if n < 1 or n > 49:
        return "?"
    year_z = _get_year_zodiac(date_str) if date_str else "馬"
    zi = ZODIAC_MAP.index(year_z)
    return ZODIAC_MAP[(zi - (n - 1)) % 12]

# Only the biggest source with text-based predictions
PRIMARY_SOURCE = "https://t.me/s/macau6hc"
SECONDARY_SOURCE = "https://t.me/s/lhczl888"  # Curated predictions + kill signals
BEFORE_HOUR = 18  # Only use data published before 18:00 local time

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".crowd_cache")
CACHE_FILE = os.path.join(CACHE_DIR, "crowd_data.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

class CrowdSentimentEngine:
    """Independent opinion direction module - big picture only.
    
    Philosophy:
    - Only extracts MAJOR trend data from the largest channel (@macau6hc, 19.9K)
    - Ignores scattered small data
    - 30% weight, only participates when today's data exists
    - No data = no effect (neutral pass-through)
    """
    
    def __init__(self, analyzer=None):
        self.a = analyzer
        self._fresh = False
        self._last_fetch = None
        self._hot_numbers = set()      # numbers being pushed as "hot"
        self._rec_numbers = set()      # numbers being recommended (⑨码/⑦码/③码)
        self._rec_zodiacs = set()      # zodiacs being recommended
        self._kill_zodiacs = set()     # zodiacs advised to avoid ("杀")
        self._kill_heads = set()       # heads advised to avoid
        self._kill_tails = set()       # tails advised to avoid
        self._load_cache()
    
    def _load_cache(self):
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if d.get("fetch_date") == date.today().isoformat():
                    self._fresh = True
                    self._last_fetch = d.get("fetch_time", "")
                    self._hot_numbers = set(d.get("hot_numbers", []))
                    self._rec_numbers = set(d.get("rec_numbers", []))
                    self._rec_zodiacs = set(d.get("rec_zodiacs", []))
                    self._kill_zodiacs = set(d.get("kill_zodiacs", []))
                    self._kill_heads = set(d.get("kill_heads", []))
                    self._kill_tails = set(d.get("kill_tails", []))
            except:
                pass
    
    def _save_cache(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "fetch_date": date.today().isoformat(),
                "fetch_time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "hot_numbers": list(self._hot_numbers),
                "rec_numbers": list(self._rec_numbers),
                "rec_zodiacs": list(self._rec_zodiacs),
                "kill_zodiacs": list(self._kill_zodiacs),
                "kill_heads": list(self._kill_heads),
                "kill_tails": list(self._kill_tails),
            }, f, ensure_ascii=False, indent=2)
    
    def _parse_time(self, post_block):
        m = re.search(r'<time[^>]*datetime="([^"]+)"', post_block)
        if m:
            try:
                return datetime.fromisoformat(m.group(1))
            except:
                pass
        return None

    def _is_before_cutoff(self, post_block):
        dt = self._parse_time(post_block)
        if dt is None:
            return True
        today = date.today()
        if dt.date() != today:
            return False
        return dt.hour < BEFORE_HOUR

    def is_data_fresh(self):
        return self._fresh
    
    def get_status(self):
        return {
            "fresh": self._fresh,
            "last_fetch": self._last_fetch,
            "source": "t.me/macau6hc (19.9K subs) + t.me/lhczl888 (6.42K subs)",
            "hot_numbers": sorted(self._hot_numbers),
            "rec_numbers": sorted(self._rec_numbers),
            "rec_zodiacs": sorted(self._rec_zodiacs),
            "kill_zodiacs": sorted(self._kill_zodiacs),
            "kill_heads": sorted(self._kill_heads),
            "kill_tails": sorted(self._kill_tails),
        }
    
    def fetch(self, timeout=20):
        """Fetch big-picture opinion data from primary source.
        Returns True if fresh prediction data was found for today.
        """
        try:
            req = urllib.request.Request(PRIMARY_SOURCE, headers={"User-Agent": UA})
            resp = urllib.request.urlopen(req, timeout=timeout,
                context=ssl._create_unverified_context())
            html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"Crowd fetch failed: {e}")
            return False
        
        today = date.today().isoformat()
        found_today = False
        
        # 1. Extract hot numbers from 50-period statistics
        # Pattern: "38：4" "25：3" etc in the stats block
        hot_section = re.search(
            r'热门开奖统计.*?号码：(.*?)生肖：', html, re.DOTALL)
        if hot_section:
            for m in re.finditer(r'(\d{1,2})：(\d+)', hot_section.group(1)):
                n, count = int(m.group(1)), int(m.group(2))
                if 1 <= n <= 49 and count >= 2:
                    self._hot_numbers.add(n)
        
        # 2. Find posts from today
        today_posts = []
        post_blocks = re.split(r'<div class="tgme_widget_message', html)
        for block in post_blocks:
            # Check if this post is from today
            date_match = re.search(r'<time[^>]*datetime="(' + today + r'[^"]*)"', block)
            if not date_match:
                continue
            # Extract text
            text = re.sub(r'<[^>]+>', ' ', block)
            text = re.sub(r'\s+', ' ', text).strip()
            if not self._is_before_cutoff(block):
                continue
            if len(text) > 20:
                today_posts.append(text)
        
        if not today_posts:
            return False
        
        # 3. Extract recommendation signals from today's posts
        all_text = " ".join(today_posts)
        
        # Pattern: "⑨码：12.34.56..." or "推荐⑨码：12.34.56..."
        for pattern in [r'[⑨⑧⑦⑥⑤④③②①]码[：:]\s*([\d.\s]+)',
                        r'推荐[⑨⑧⑦⑥⑤④③②①]码[：:]\s*([\d.\s]+)']:
            for m in re.finditer(pattern, all_text):
                nums = re.findall(r'\d{1,2}', m.group(1))
                for ns in nums:
                    n = int(ns)
                    if 1 <= n <= 49:
                        self._rec_numbers.add(n)
        
        # Pattern: "⑨肖：鸡羊狗..." 
        zodiac_names = ['鼠','牛','虎','兔','龙','蛇','马','羊','猴','鸡','狗','猪']
        for pattern in [r'[⑨⑧⑦⑥⑤④③②①]肖[：:]\s*([^0-9\n]{2,30})']:
            for m in re.finditer(pattern, all_text):
                for z in zodiac_names:
                    if z in m.group(1):
                        self._rec_zodiacs.add(z)
        
        # Pattern: "平特一肖：蛇"
        for m in re.finditer(r'平特一肖[：:]\s*(\S)', all_text):
            z = m.group(1)
            if z in zodiac_names:
                self._rec_zodiacs.add(z)
        
        # 4. Extract "kill" signals (杀肖/杀头/杀尾)
        # "绝杀三肖" means they advise avoiding 3 zodiacs
        # These are signals of what bettors are told to avoid → potential opportunity
        kill_zod_match = re.search(r'杀.*?肖.*?[:：]\s*([^0-9\n]{2,30})', all_text)
        if kill_zod_match:
            for z in zodiac_names:
                if z in kill_zod_match.group(1):
                    self._kill_zodiacs.add(z)
        
        kill_head_match = re.search(r'杀.*?头.*?[:：]\s*([\d.\s]+)', all_text)
        if kill_head_match:
            for ns in re.findall(r'\d', kill_head_match.group(1)):
                self._kill_heads.add(int(ns))
        
        # 5. Validate: do we have enough meaningful data?
        if len(self._rec_numbers) >= 3 or len(self._hot_numbers) >= 5:
            self._fresh = True
            self._last_fetch = datetime.now().strftime("%Y-%m-%d %H:%M")
            self._save_cache()
            return True
        
        return False
    
    def fetch_lhczl888(self, timeout=20):
        try:
            req = urllib.request.Request(SECONDARY_SOURCE, headers={"User-Agent": UA})
            resp = urllib.request.urlopen(req, timeout=timeout,
                context=ssl._create_unverified_context())
            html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"lhczl888 fetch failed: {e}")
            return

        post_blocks = re.split(r'<div class="tgme_widget_message', html)
        today_posts = []

        for block in post_blocks:
            if not self._is_before_cutoff(block):
                continue
            text = re.sub(r'<[^>]+>', ' ', block)
            text = re.sub(r'\s+', ' ', text).strip()
            if len(text) > 20:
                today_posts.append(text)

        if not today_posts:
            return

        all_text = " ".join(today_posts)

        # kill head: shaxNtou
        for m in re.finditer(r'杀(\d)头', all_text):
            self._kill_heads.add(int(m.group(1)))

        # kill tail: shaNwei or shaN/Mwei
        for m in re.finditer(r'杀([\d/]+)尾', all_text):
            for t in re.findall(r'\d', m.group(1)):
                self._kill_tails.add(int(t))

        # recommendations
        for pattern in [r'心[\s]*水[：:]\s*([\d.\s,，]+)', r'推[\s]*荐[：:]\s*([\d.\s,，]+)']:
            for m in re.finditer(pattern, all_text):
                for ns in re.findall(r'\d{1,2}', m.group(1)):
                    n = int(ns)
                    if 1 <= n <= 49:
                        self._rec_numbers.add(n)

    def fetch_all(self, timeout=20):
        self.fetch(timeout=timeout)
        self.fetch_lhczl888(timeout=timeout)
        return self._fresh

    def update_manual(self, hot_numbers_list):
        """Manual input: [(num, heat), ...] or [num, ...]"""
        self._rec_numbers.clear()
        for item in hot_numbers_list:
            n = item[0] if isinstance(item, (list, tuple)) else item
            self._rec_numbers.add(int(n))
        self._fresh = True
        self._last_fetch = datetime.now().strftime("%Y-%m-%d %H:%M")
        self._save_cache()
    
    def compute_reverse_weights(self):
        """Compute reverse weights (0.3-1.0) for all 49 numbers.
        
        Logic:
        - Numbers in BOTH hot + rec lists → heaviest penalty (0.3)
        - Numbers in rec list → heavy penalty (0.5)
        - Numbers in hot list → moderate penalty (0.7)
        - Numbers with kill signal zodiac → boost (1.2)
        - Others → neutral (1.0)
        
        Returns None if data not fresh.
        """
        if not self._fresh:
            return None
        
        weights = {}
        for n in range(1, 50):
            w = 1.0
            
            # Penalize: recommended numbers (masses will bet on these)
            in_rec = n in self._rec_numbers
            in_hot = n in self._hot_numbers
            
            if in_rec and in_hot:
                w = 0.3   # double confirmation = house definitely avoids
            elif in_rec:
                w = 0.5   # recommended = likely avoided
            elif in_hot:
                w = 0.7   # hot = some avoidance
            
            # Boost: numbers from "kill" zodiacs
            # "Kill sheep" means bettors avoid sheep → house might open sheep
            n_zodiac = _num_to_zodiac(n)
            if n_zodiac and n_zodiac in self._kill_zodiacs:
                w = min(1.3, w * 1.3)
            
            # Additional: avoid numbers in kill head/tail ranges
            head = n // 10
            tail = n % 10
            if head in self._kill_heads:
                w = min(1.2, w * 1.15)
            
            weights[n] = round(min(max(w, 0.3), 1.3), 3)
        
        return weights

print("CrowdSentimentEngine v2 ready - big picture only")