"""MacauLottery v4PRO — Android APP (Responsive + Android 13/14/15 Compatible)
遵循 Android 开发者文档：
  - minSdkVersion 33 (Android 13, 2023+)
  - targetSdkVersion 35 (Android 15, latest)
  - 响应式布局：基于 dp 密度自适应缩放
  - 基准设计宽度 360dp（标准手机）
"""
import sys, os
_cur = os.path.dirname(os.path.abspath(__file__))
# shared/ location: dev=../shared, packaged=./shared
for _sd in [os.path.join(_cur, '..', 'shared'), os.path.join(_cur, 'shared')]:
    if os.path.isdir(_sd):
        sys.path.insert(0, _sd)
sys.path.insert(0, _cur)
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import flet as ft
from shared.engine import (
    LotteryAnalyzer, AdversarialPredictor, EnsemblePredictor,
    load_data,
    num_to_zodiac, num_to_wave, num_to_odd_even, num_to_wuxing, sync_latest,
    ZODIAC_MAP
)

# 生肖排序 (list没有get方法, 建立索引映射)
ZODIAC_ORDER = {z: i for i, z in enumerate(ZODIAC_MAP)}

# 家禽/野兽分类 (澳门六合彩标准: 牛马羊鸡狗猪=家禽, 其余=野兽)
POULTRY = {"牛", "馬", "羊", "雞", "狗", "豬"}

# Also: directly inline the check in sp_labels to avoid extra function calls
# 五行已在 engine 中通过 num_to_wuxing 返回, 家禽/野兽在此判断


# ───────────────────────── 自适应缩放 ─────────────────────────
class AdaptiveScale:
    """基于 360dp 基准宽度的缩放引擎"""
    BASE_WIDTH = 360.0
    MIN_SCALE = 0.82
    MAX_SCALE = 1.55
    
    def __init__(self):
        self.scale = 1.0
        self.screen_w = 360
        self.screen_h = 640
    
    def update(self, width, height):
        self.screen_w = max(width, 1)
        self.screen_h = max(height, 1)
        raw = min(self.screen_w, self.screen_h) / self.BASE_WIDTH
        self.scale = max(self.MIN_SCALE, min(self.MAX_SCALE, raw))
    
    def s(self, base_size):
        """缩放尺寸，返回整数"""
        return max(1, int(round(base_size * self.scale)))
    
    def fs(self, base_size):
        """缩放字号"""
        return base_size * self.scale
    
    def pad(self, base):
        """缩放 padding (四边相同)"""
        v = self.s(base)
        return ft.Padding(left=v, top=v, right=v, bottom=v)
    
    def pad_symmetric(self, horizontal, vertical):
        """缩放 padding (水平/垂直)"""
        return ft.Padding(
            left=self.s(horizontal), top=self.s(vertical),
            right=self.s(horizontal), bottom=self.s(vertical)
        )
    
    def margin_bottom(self, base):
        return ft.Margin(left=0, top=0, right=0, bottom=self.s(base))
    
    def ball_size(self):
        s = self.s(34)
        return s, s // 2  # (size, radius)
    
    @property
    def header_size(self): return self.fs(20)
    @property
    def title_size(self): return self.fs(15)
    @property
    def body_size(self): return self.fs(13)
    @property
    def small_size(self): return self.fs(10)
    @property
    def tiny_size(self): return self.fs(8)
    @property
    def mono_size(self): return self.fs(9)
    @property
    def prediction_size(self): return self.fs(20)
    @property
    def zodiac_large_size(self): return self.fs(18)
    @property
    def btn_text_size(self): return self.fs(12)
    @property
    def btn_height(self): return self.s(38)

# 全局缩放实例
adp = AdaptiveScale()


# ───────────────────────── 主 APP ─────────────────────────
class MacauApp:
    def __init__(self, page: ft.Page):
        self.page = page
        page.title = "数字游戏预测 V4PRO"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = "#0d1117"
        page.padding = adp.s(8)
        page.scroll = ft.ScrollMode.AUTO
        
        self.analyzer = None
        self.ensemble = None
        self.data = None
        self._current_tab = 0
        
        # ── 响应式窗口尺寸检测 ──
        page.on_resize = self._on_resize
        
        # ── Header ──
        self.header_text = ft.Text(
            "数字游戏预测 V4PRO",
            size=adp.header_size, weight=ft.FontWeight.BOLD, color="#f5c518"
        )
        self.status = ft.Text("加载中...", color="#8b949e", size=adp.small_size)
        self.sync_btn = ft.Button(
            content=ft.Text("↻ 同步", size=adp.s(10), color="#8b949e"),
            on_click=self._sync_now,
            height=adp.s(26),
            style=ft.ButtonStyle(
                bgcolor="#161b22",
                padding=adp.pad_symmetric(8, 2),
            ),
        )
        page.add(ft.Row([self.header_text], alignment=ft.MainAxisAlignment.CENTER))
        page.add(ft.Row([self.status, self.sync_btn],
                        alignment=ft.MainAxisAlignment.CENTER, spacing=adp.s(8)))
        
        # ── Tab Buttons (Material 3 风格) ──
        self._make_tabs()
        page.add(self.tab_row)
        
        # ── Content ──
        self.content_area = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        page.add(self.content_area)
        
        # 初始尺寸检测
        if page.width and page.height:
            adp.update(page.width, page.height)
        else:
            adp.update(360, 640)  # 默认手机尺寸
        
        self.load_data()
    
    def _on_resize(self, e):
        """窗口尺寸变化时重新缩放"""
        if self.page.width and self.page.height:
            adp.update(self.page.width, self.page.height)
        self._refresh_ui()
    
    def _make_tabs(self):
        def btn(label, idx):
            return ft.Button(
                content=ft.Text(label, size=adp.btn_text_size),
                on_click=lambda e: self.show_page(idx),
                bgcolor="#e94560" if idx == 0 else "#161b22",
                color="white" if idx == 0 else "#8b949e",
                height=adp.btn_height,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=adp.s(6)),
                    padding=adp.pad_symmetric(14, 6),
                ),
            )
        
        self.tab_btns = [
            btn("预测", 0),
            btn("分析", 1),
            btn("历史", 2),
            btn("追踪", 3),
        ]
        self.tab_row = ft.Row(

            controls=self.tab_btns + [
                ft.Button(
                    content=ft.Text("录入", size=adp.btn_text_size),
                    on_click=lambda e: self.show_manual_entry(),
                    bgcolor="#3fb950",
                    color="#000000",
                    height=adp.btn_height,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=adp.s(6)),
                        padding=adp.pad_symmetric(14, 6),
                    ),
                ),
            ],
            spacing=adp.s(6),
            alignment=ft.MainAxisAlignment.CENTER,
            wrap=True,
        )
    def _refresh_ui(self):
        """完整的 UI 刷新（缩放变化时）"""
        adp.update(self.page.width or 360, self.page.height or 640)
        self.header_text.size = adp.header_size
        self.status.size = adp.small_size
        self._make_tabs()
        # 重建 tab row
        self.page.controls[2] = self.tab_row
        self.show_page(self._current_tab)
    
    def show_page(self, idx):
        self._current_tab = idx
        base = "#161b22"
        colors = [base, base, base, base]
        colors[idx] = "#e94560"
        for i, btn in enumerate(self.tab_btns):
            btn.bgcolor = colors[i]
            btn.color = "white" if i == idx else "#8b949e"
        
        if idx == 0:
            self.show_predict()
        elif idx == 1:
            self.show_analysis()
        elif idx == 2:
            self.show_history()
        elif idx == 3:
            self.show_zodiac_track()
    
    def load_data(self):
        import traceback
        try:
            self.data = load_data()
            self.analyzer = LotteryAnalyzer(self.data)
            self.ensemble = EnsemblePredictor(self.analyzer)
            self.status.value = f"{len(self.data)} 条记录 | 就绪"
            self.status.color = "#3fb950"
            # 启动后异步拉取最新数据
            import threading
            threading.Thread(target=self._background_sync, daemon=True).start()
        except Exception as e:
            traceback.print_exc()
            self.status.value = f"加载失败: {e}"
            self.status.color = "#f85149"
            return
        self.show_page(0)
    
    def _background_sync(self):
        """后台异步同步API最新数据"""
        import time
        time.sleep(2)  # 等UI完全渲染
        try:
            self.status.value = f"{len(self.data)} 条记录 | 同步中..."
            self.status.color = "#f5c518"
            if hasattr(self, 'page') and self.page:
                self.page.update()
            
            new_count, total = sync_latest()
            if new_count > 0:
                # 重新加载数据
                self.data = load_data()
                self.analyzer = LotteryAnalyzer(self.data)
                self.ensemble = EnsemblePredictor(self.analyzer)
                self.status.value = f"{total} 条记录 | +{new_count} 新数据"
                self.status.color = "#3fb950"
            else:
                self.status.value = f"{total} 条记录 | 已是最新"
                self.status.color = "#3fb950"
        except Exception as e:
            self.status.value = f"{len(self.data)} 条记录 | 同步失败"
            self.status.color = "#f85149"
        if hasattr(self, 'page') and self.page:
            self.page.update()
            # 刷新当前页
            if self._current_tab is not None:
                self.show_page(self._current_tab)
    
    def _sync_now(self, e=None):
        """手动刷新按钮"""
        self.sync_btn.disabled = True
        self.status.value = f"{len(self.data)} 条记录 | 同步中..."
        self.status.color = "#f5c518"
        self.page.update()
        import threading
        threading.Thread(target=self._do_sync, daemon=True).start()
    
    def _do_sync(self):
        try:
            new_count, total = sync_latest()
            if new_count > 0:
                self.data = load_data()
                self.analyzer = LotteryAnalyzer(self.data)
                self.ensemble = EnsemblePredictor(self.analyzer)
                self.status.value = f"{total} 条记录 | +{new_count} 新数据"
                self.status.color = "#3fb950"
            else:
                self.status.value = f"{total} 条记录 | 已是最新"
                self.status.color = "#3fb950"
        except Exception as e:
            self.status.value = f"{len(self.data)} 条记录 | 同步失败"
            self.status.color = "#f85149"
        self.sync_btn.disabled = False
        if hasattr(self, 'page') and self.page:
            self.page.update()
            if self._current_tab is not None:
                self.show_page(self._current_tab)
    
    # ──────────────── UI 组件 ────────────────
    def _card(self, children, color="#161b22", accent=None):
        """Material 3 风格卡片"""
        border = None
        if accent:
            border = ft.Border(left=ft.BorderSide(adp.s(3), accent))
        return ft.Container(
            ft.Column(children, spacing=adp.s(3)),
            padding=adp.pad(10),
            bgcolor=color,
            border_radius=adp.s(8),
            margin=adp.margin_bottom(7),
            border=border,
        )
    
    def _section_title(self, text, color="#f5c518"):
        return ft.Text(text, size=adp.title_size, weight=ft.FontWeight.BOLD, color=color)
    
    def _sub_title(self, text, color="#8b949e"):
        return ft.Text(text, size=adp.small_size, color=color)
    
    def _num_ball(self, n, ball_size, text_size, zodiac_size=None, show_zodiac=True, show_wave=False):
        """创建彩色号码方块 (波色底色 + 号码 + 可选生肖/波色)"""
        _, wave_color = num_to_wave(n)
        z = num_to_zodiac(n)
        wv, _ = num_to_wave(n)
        r = ball_size // 2
        children = [ft.Text(str(n), size=text_size, color="white", weight=ft.FontWeight.BOLD)]
        if show_zodiac and zodiac_size:
            children.append(ft.Text(z, size=zodiac_size, color="rgba(255,255,255,0.8)"))
        if show_wave:
            children.append(ft.Text(wv, size=max(7, zodiac_size-1) if zodiac_size else 8, color="rgba(255,255,255,0.65)"))
        return ft.Container(
            ft.Column(children, spacing=adp.s(-2) if len(children) > 1 else 0,
                      alignment=ft.MainAxisAlignment.CENTER,
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=ball_size, height=ball_size,
            bgcolor=wave_color,
            border_radius=adp.s(4),
            alignment=ft.alignment.Alignment(0, 0),
        )
    
    def _history_ball_size(self):
        """计算历史页每期刚好一排的球大小"""
        avail = adp.screen_w - adp.s(16) - adp.s(20)  # screen - outer_padding - card_padding
        text_w = adp.s(42) + adp.s(68)  # #id + date
        gaps = adp.s(9)  # 8 gaps between 9 items
        ball_max = (avail - text_w - gaps) // 7
        return max(24, min(34, ball_max))
    
    # ──────────────── 预测页 ────────────────
    def show_predict(self):
        self.content_area.controls.clear()
        if not self.analyzer:
            self.content_area.controls.append(ft.ProgressRing())
            self.page.update()
            return
        
        a = self.analyzer
        try:
            lt = self.data[-1]
            nums = a.get_numbers(lt)
            
            # 最新开奖
            bs = adp.s(40)
            draw_balls = [self._num_ball(n, bs, adp.s(14), adp.s(9), show_zodiac=True) for n in nums]
            self.content_area.controls.append(self._card([
                self._section_title("最新开奖"),
                self._sub_title(f"#{lt.get('expect','?')} | {lt.get('openTime','')}"),
                ft.Row(draw_balls, spacing=adp.s(3), wrap=True, scroll=ft.ScrollMode.AUTO),
            ], accent="#f5c518"))
            
            # 预测
            pred = self.ensemble.adversarial.predict_specials(8)
            triple = a.predict_triple_zodiac()
            quad = a.predict_quad_zodiac()
            
            self.content_area.controls.append(self._card([
                self._section_title("三连肖预测", "#3fb950"),
                ft.Text("  ".join(f"[{z}]" for z in triple), size=adp.zodiac_large_size, color="#3fb950", weight=ft.FontWeight.BOLD),
            ], accent="#3fb950"))
            
            self.content_area.controls.append(self._card([
                self._section_title("四连肖预测", "#f85149"),
                ft.Text("  ".join(f"[{z}]" for z in quad), size=adp.prediction_size, color="#f85149", weight=ft.FontWeight.BOLD),
            ], accent="#f85149"))
            
            # 特码推荐 — 单排自适应球 (8球始终一行)
            count = len(pred)
            avail_w = adp.screen_w - adp.s(16) - adp.s(20)  # screen - outer - card
            gap_total = adp.s(3) * (count - 1)
            sp_bs = max(adp.s(28), min(adp.s(48), (avail_w - gap_total) // count))
            sp_fs = max(adp.s(9), sp_bs // 3)
            sp_zs = max(adp.s(6), sp_bs // 5)
            
            sp_balls = []
            sp_labels = []
            for n in pred:
                sp_balls.append(self._num_ball(n, sp_bs, sp_fs, sp_zs, show_zodiac=True, show_wave=False))
                wx = num_to_wuxing(n)
                jy = "家禽" if num_to_zodiac(n) in {"牛","馬","羊","雞","狗","豬"} else "野兽"
                sp_labels.append(ft.Text(f"{wx}·{jy}", size=sp_zs, color="#8b949e", text_align=ft.TextAlign.CENTER, width=sp_bs))
            
            self.content_area.controls.append(self._card([
                self._section_title("特码推荐", "#58a6ff"),
                ft.Row(sp_balls, spacing=adp.s(3), wrap=False,
                       alignment=ft.MainAxisAlignment.SPACE_EVENLY),
                ft.Row(sp_labels, spacing=adp.s(3),
                       alignment=ft.MainAxisAlignment.SPACE_EVENLY),
            ], accent="#58a6ff"))
            
            # 策略建议
            wc = a.wave_stats(100)
            oc = a.odd_even_stats(100)
            hot, cold, _ = a.hot_cold_numbers(50)
            total_oe = sum(oc.values()) or 1
            # 一码中特
            top_one = pred[0]
            oz = num_to_zodiac(top_one)
            ow, wc_color = num_to_wave(top_one)
            ooe, _ = num_to_odd_even(top_one)
            top_house = self.ensemble._house_strategy()
            th = top_house.get(top_one, 0.5)
            
            yms_size = adp.s(48)
            self.content_area.controls.append(self._card([
                self._section_title("一码中特", "#f5c518"),
                ft.Row([
                    ft.Text(f"{top_one:02d}", size=yms_size, color=wc_color, weight=ft.FontWeight.BOLD),
                    ft.Column([
                        ft.Text(f"生肖: {oz}", size=adp.body_size, color="#e6edf3"),
                        ft.Text(f"波色: {ow}", size=adp.body_size, color=oc),
                        ft.Text(f"单双: {ooe}", size=adp.body_size, color="#e6edf3"),
                        ft.Text(f"庄家意愿: {th:.0%}", size=adp.small_size, color="#8b949e"),
                    ], spacing=adp.s(2)),
                ], spacing=adp.s(16), alignment=ft.MainAxisAlignment.CENTER),
            ], accent="#f5c518"))
            
            total_oe = sum(oc.values()) or 1
            
            advice_lines = [
                f"• 热号: {hot[0]:02d}({num_to_zodiac(hot[0])}) {hot[1]:02d}({num_to_zodiac(hot[1])}) {hot[2]:02d}({num_to_zodiac(hot[2])})",
                f"• 冷号: {cold[0]:02d}({num_to_zodiac(cold[0])}) {cold[1]:02d}({num_to_zodiac(cold[1])}) {cold[2]:02d}({num_to_zodiac(cold[2])})",
                f"• 波色: 红{wc.get('红波',0)} 蓝{wc.get('蓝波',0)} 绿{wc.get('绿波',0)}",
                f"• 单双: 单{oc.get('单',0)/total_oe*100:.0f}% 双{oc.get('双',0)/total_oe*100:.0f}%",
            ]
            
            self.content_area.controls.append(self._card([
                self._section_title("综合策略", "#d2a8ff"),
                ft.Text("\n".join(advice_lines), size=adp.small_size, color="#e6edf3"),
            ], accent="#d2a8ff"))
            
            # ── 生肖追踪板块 ──
            # 生肖追踪已独立为标签页
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.content_area.controls.append(ft.Text(f"预测错误: {e}", color="#f85149"))
        
        self.page.update()
    
    # ──────────────── 生肖追踪页 ────────────────
    def show_zodiac_track(self):
        """生肖追踪 — 对标 PC 端：180期未开期数柱状图"""
        self.content_area.controls.clear()
        if not self.analyzer:
            self.content_area.controls.append(ft.ProgressRing())
            self.page.update()
            return
        
        a = self.analyzer
        try:
            # ── 180期生肖间距 (特码位置) ──
            last_n = min(180, len(self.data))
            recent = self.data[-last_n:]
            gap = {z: last_n for z in ZODIAC_MAP}
            latest_zodiac = None
            if recent:
                nums = a.get_numbers(recent[-1])
                if len(nums) >= 7:
                    latest_zodiac = num_to_zodiac(nums[6])
            for i, r in enumerate(reversed(recent)):
                nums = a.get_numbers(r)
                if len(nums) >= 7:
                    z = num_to_zodiac(nums[6])
                    if gap[z] == last_n:
                        gap[z] = i
            
            # ── 基础统计 ──
            zc = {}
            for r in recent:
                nums = a.get_numbers(r)
                for n in nums:
                    z = num_to_zodiac(n)
                    zc[z] = zc.get(z, 0) + 1
            
            max_gap = max(max(gap.values()), 1)
            bar_area_h = adp.s(200)
            
            # ── 柱状图 (自适应) ──
            bars = []
            n_bars = 12
            avail_w = adp.screen_w - adp.s(32) - adp.s(20)
            bar_w = max(adp.s(18), (avail_w // n_bars) - adp.s(6))
            
            bar_row_controls = []
            label_row_controls = []
            
            for z in ZODIAC_MAP:
                g = gap[z]
                bh = max(adp.s(6), int((g / max_gap) * bar_area_h)) if g > 0 else adp.s(6)
                
                # 颜色: 绿(0期已开) → 黄(≤5) → 橙(≤10) → 红(≤20) → 深红(>20)
                if g == 0:
                    bar_color = "#3fb950"
                elif g <= 5:
                    bar_color = "#4ae04a"
                elif g <= 10:
                    bar_color = "#f5c518"
                elif g <= 15:
                    bar_color = "#ff8c00"
                elif g <= 20:
                    bar_color = "#ff6644"
                else:
                    bar_color = "#f85149"
                
                bar_row_controls.append(ft.Column([
                    ft.Text(str(g) if g > 0 else "已开", size=adp.s(8), color="#8b949e", text_align=ft.TextAlign.CENTER),
                    ft.Container(
                        width=bar_w, height=bh,
                        bgcolor=bar_color,
                        border_radius=adp.s(3),
                    ),
                ], spacing=adp.s(2), alignment=ft.MainAxisAlignment.END,
                   horizontal_alignment=ft.CrossAxisAlignment.CENTER))
                
                label_row_controls.append(ft.Container(
                    ft.Text(z, size=adp.s(10), color="#e6edf3", weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                    width=bar_w + adp.s(4),
                    alignment=ft.alignment.Alignment(0, 0),
                ))
            
            self.content_area.controls.append(self._card([
                self._section_title("特码生肖未开期数 · 近180期", "#f5c518"),
                ft.Text(f"最新特码生肖: {latest_zodiac or '---'}", size=adp.small_size, color="#3fb950"),
                ft.Container(height=adp.s(8)),
                ft.Row(bar_row_controls, spacing=adp.s(4),
                       alignment=ft.MainAxisAlignment.CENTER,
                       vertical_alignment=ft.CrossAxisAlignment.END),
                ft.Row(label_row_controls, spacing=adp.s(2),
                       alignment=ft.MainAxisAlignment.CENTER),
            ], accent="#f5c518"))
            
            # ── 生肖统计表 ──
            stat_rows = []
            for z in sorted(ZODIAC_MAP, key=lambda x: gap.get(x, 999)):
                g = gap[z]
                c = zc.get(z, 0)
                g_color = "#3fb950" if g == 0 else ("#f85149" if g > 10 else "#f5c518")
                stat_rows.append(
                    ft.Row([
                        ft.Text(z, size=adp.s(11), color="#e6edf3", weight=ft.FontWeight.BOLD, width=adp.s(32)),
                        ft.Text(f"特码缺{g}期" if g > 0 else "特码已开", size=adp.s(10), color=g_color, width=adp.s(72)),
                        ft.Text(f"近180期出现{c}次", size=adp.s(10), color="#8b949e"),
                    ], spacing=adp.s(4))
                )
            
            self.content_area.controls.append(self._card([
                self._section_title("生肖详细统计", "#58a6ff"),
                ft.Column(stat_rows, spacing=adp.s(3)),
            ], accent="#58a6ff"))
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.content_area.controls.append(ft.Text(f"追踪错误: {e}", color="#f85149"))
        
        self.page.update()
    
    # ──────────────── 分析页 ────────────────
    def show_analysis(self):
        self.content_area.controls.clear()
        if not self.analyzer:
            self.content_area.controls.append(ft.ProgressRing())
            self.page.update()
            return
        
        a = self.analyzer
        try:
            nc, zc = a.frequency_stats(100)
            hot, cold, _ = a.hot_cold_numbers(50)
            
            # 频率柱状图 (紧凑版，自适应宽度)
            max_bar = min(adp.s(18), 18)
            freq_lines = []
            for n in range(1, 50):
                c = nc.get(n, 0)
                bar_len = min(c, max_bar)
                bar = "█" * bar_len
                z = num_to_zodiac(n)
                tag = "🔥" if c > 15 else ("❄️" if c < 8 else "")
                freq_lines.append(f"{n:02d}({z}) {bar} {c}{tag}")
            
            self.content_area.controls.append(self._card([
                self._section_title("号码频率 近100期", "#3fb950"),
                ft.Text("\n".join(freq_lines), size=adp.mono_size, font_family="monospace", color="#e6edf3"),
            ]))
            
            # 冷热号
            hot_s = " ".join(f"{x:02d}({num_to_zodiac(x)})" for x in hot)
            cold_s = " ".join(f"{x:02d}({num_to_zodiac(x)})" for x in cold)
            self.content_area.controls.append(self._card([
                self._section_title("冷热号分析", "#f85149"),
                ft.Text(f"🔥 HOT: {hot_s}", size=adp.small_size, color="#ffa657"),
                ft.Text(f"❄️ COLD: {cold_s}", size=adp.small_size, color="#58a6ff"),
            ], accent="#f85149"))
            
            # 生肖频率
            z_lines = []
            for z in sorted(ZODIAC_MAP, key=lambda x: zc.get(x, 0), reverse=True):
                c = zc.get(z, 0)
                bar = "█" * min(c, max_bar)
                z_lines.append(f"{z}  {bar} {c}")
            
            self.content_area.controls.append(self._card([
                self._section_title("生肖频率", "#f5c518"),
                ft.Text("\n".join(z_lines), size=adp.small_size, font_family="monospace", color="#f5c518"),
            ]))
            
            # 波色/单双
            wc = a.wave_stats(100)
            oc = a.odd_even_stats(100)
            total_oe = sum(oc.values()) or 1
            w_text = "  ".join(f"{w}:{wc.get(w,0)}" for w in ["红波","蓝波","绿波"])
            o_text = f"单:{oc.get('单',0)}({oc.get('单',0)/total_oe*100:.0f}%)  双:{oc.get('双',0)}({oc.get('双',0)/total_oe*100:.0f}%)"
            
            self.content_area.controls.append(self._card([
                self._section_title("波色/单双", "#7b2ff7"),
                ft.Text(w_text, size=adp.body_size, color="#e6edf3"),
                ft.Text(o_text, size=adp.body_size, color="#e6edf3"),
            ]))
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.content_area.controls.append(ft.Text(f"分析错误: {e}", color="#f85149"))
        
        self.page.update()
    
    # ──────────────── 历史页 ────────────────
    def show_history(self):
        self.content_area.controls.clear()
        if not self.analyzer:
            self.content_area.controls.append(ft.ProgressRing())
            self.page.update()
            return
        
        a = self.analyzer
        try:
            ball_s = self._history_ball_size()
            items = []
            for r in reversed(self.data[-120:]):
                ex = r.get("expect", "")[-4:]
                ts = (r.get("openTime", "") or "")[:10]
                nums = a.get_numbers(r)
                
                balls = []
                for i_n, n in enumerate(nums):
                    prefix = "+" if i_n == 6 else ""
                    balls.append(self._num_ball(n, ball_s, adp.s(10), adp.s(7), show_zodiac=True))
                    # 特码加标记
                    if prefix:
                        b = balls[-1]
                
                items.append(ft.Row([
                    ft.Text(f"#{ex}", size=adp.s(9), color="#8b949e", width=adp.s(40)),
                    ft.Text(ts, size=adp.s(9), color="#8b949e", width=adp.s(65)),
                    *balls,
                ], spacing=adp.s(1), wrap=False,
                   vertical_alignment=ft.CrossAxisAlignment.CENTER))
            
            self.content_area.controls.append(self._card([
                self._section_title("开奖历史 最新120期", "#f5c518"),
                *items,
            ]))
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.content_area.controls.append(ft.Text(f"历史错误: {e}", color="#f85149"))
        
        self.page.update()



    # ──────────────── 手动录入开奖数据 ────────────────
    def show_manual_entry(self):
        """手动录入开奖数据对话框"""
        global _manual_dlg_data
        _manual_dlg_data = {"expect": "", "date": "", "codes": ""}
        
        if self.data:
            lt = self.data[-1]
            _manual_dlg_data["expect"] = str(int(lt.get("expect", 0)) + 1)
            _manual_dlg_data["date"] = (lt.get("openTime", "") or "")[:10]
        
        expect_field = ft.TextField(
            label="期号", value=_manual_dlg_data["expect"],
            border_color="#f5c518", text_size=adp.body_size,
            bgcolor="#0d1117", color="#e6edf3",
            on_change=lambda e: _manual_dlg_data.update({"expect": e.control.value}),
        )
        date_field = ft.TextField(
            label="日期 (YYYY-MM-DD)", value=_manual_dlg_data["date"],
            border_color="#f5c518", text_size=adp.body_size,
            bgcolor="#0d1117", color="#e6edf3",
            on_change=lambda e: _manual_dlg_data.update({"date": e.control.value}),
        )
        codes_field = ft.TextField(
            label="号码 (逗号分隔，6平特+1正特)", value="",
            border_color="#58a6ff", text_size=adp.body_size,
            bgcolor="#0d1117", color="#e6edf3", hint_text="如: 05,12,23,34,41,48,07",
            hint_style=ft.TextStyle(color="#484f58"),
            on_change=lambda e: _manual_dlg_data.update({"codes": e.control.value}),
        )
        
        status_text = ft.Text("", size=adp.small_size, color="#f85149")
        
        def do_save(e):
            codes_str = _manual_dlg_data["codes"].strip()
            if not codes_str:
                status_text.value = "请输入号码"
                status_text.update()
                return
            
            parts = [p.strip() for p in codes_str.replace("，", ",").split(",") if p.strip()]
            if len(parts) != 7:
                status_text.value = f"需要7个号码，当前{len(parts)}个"
                status_text.update()
                return
            try:
                nums = [int(p) for p in parts]
                if not all(1 <= n <= 49 for n in nums):
                    status_text.value = "号码必须在1-49之间"
                    status_text.update()
                    return
            except ValueError:
                status_text.value = "号码格式错误"
                status_text.update()
                return
            
            codes_fmt = ",".join(f"{n:02d}" for n in nums)
            new_record = {
                "expect": _manual_dlg_data["expect"],
                "openCode": codes_fmt,
                "openTime": (_manual_dlg_data["date"] or "") + " 21:30:00"
            }
            existing = load_data()
            existing = [d for d in existing if d.get("expect") != _manual_dlg_data["expect"]]
            existing.append(new_record)
            all_data = sorted(existing, key=lambda x: int(x.get("expect", 0)))
            save_data(all_data)
            
            self.data = sorted(load_data(), key=lambda x: int(x.get("expect", 0)))
            self.analyzer = LotteryAnalyzer(self.data)
            self.ensemble = EnsemblePredictor(self.analyzer)
            self.page.dialog.open = False
            self.page.update()
            self.show_predict()
        
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("手动录入开奖数据", color="#f5c518", weight=ft.FontWeight.BOLD),
            content=ft.Column([
                expect_field,
                date_field,
                codes_field,
                status_text,
            ], spacing=adp.s(10), tight=True, height=adp.s(260), width=adp.s(300)),
            actions=[
                ft.TextButton("取消", on_click=lambda e: setattr(self.page.dialog, "open", False) or self.page.update()),
                ft.ElevatedButton("确认录入", on_click=do_save,
                    bgcolor="#3fb950", color="#000000"),
            ],
            bgcolor="#161b22",
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

def main():
    ft.run(MacauApp, name="数字游戏预测V4PRO")

if __name__ == "__main__":
    main()