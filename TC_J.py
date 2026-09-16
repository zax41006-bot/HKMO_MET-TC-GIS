import time
import os
import pandas as pd
import numpy as np
import datetime
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.geodesic as cgeo
from scipy.interpolate import PchipInterpolator
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from matplotlib.lines import Line2D
import tcmarkers

# ==================== 1. 氣旋與 GitHub Pages 網址設定 ====================
TC_ID = "J"
TC_NAME = "杜鵑"

# 你的 GitHub Pages 基礎網址
SITE_BASE_URL = "https://zax41006-bot.github.io/TC-Track"

PAST_CSV_URL = f"{SITE_BASE_URL}/past_track_{TC_ID}.csv"
FORE_CSV_URL = f"{SITE_BASE_URL}/forecast_track_{TC_ID}.csv"

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
OUTPUT_IMG = os.path.join(BASE_PATH, f"TC_forecast_{TC_ID}.png")

plt.rcParams["font.family"] = ["Microsoft YaHei", "SimHei", "Microsoft JhengHei"]
plt.rcParams["axes.unicode_minus"] = False

# 港澳座標設定
MACAO_LON, MACAO_LAT = 113.55, 22.17
HK_LON, HK_LAT = 114.17, 22.32

# ==================== 強度代碼 → 顏色 / 中文名稱 對照表 ====================
INTENSITY_MAP = {
    "LPA":     ("低壓區",       "#C5C9CE"),
    "MD":      ("季風低壓",     "#C5C9CE"),   
    "TD":      ("熱帶低氣壓",   "#FFF08A"),
    "TS":      ("熱帶風暴",     "#5FA8E0"),
    "STS":     ("強烈熱帶風暴", "#4CAF50"),
    "TY":      ("颱風",         "#F5A623"),
    "STY":     ("強颱風",       "#EF6C3A"),
    "SUTY":    ("超強颱風",     "#A056C4"),   
    "EX":      ("溫帶氣旋",     "#9E9E9E"),   
}

def get_intensity_code(wind, cyc_type="tropical"):
    """依風速推算強度代碼（僅在 CSV 無 intensity 欄位時作為後備）"""
    if cyc_type == "EX": return "EX"
    if wind < 41: return "LPA"
    elif wind <= 62: return "TD"
    elif wind <= 87: return "TS"
    elif wind <= 117: return "STS"
    elif wind <= 149: return "TY"
    elif wind <= 184: return "STY"
    else: return "SUTY"  

def get_intensity_by_code(code):
    """依強度代碼回傳 (中文名稱, 顏色)"""
    return INTENSITY_MAP.get(str(code).strip().upper(), INTENSITY_MAP["LPA"])

def get_intensity_info(wind, cyc_type="tropical"):
    """保留舊接口：依風速回傳 (中文名稱, 顏色, 圖示)"""
    code = get_intensity_code(wind, cyc_type)
    name, color = get_intensity_by_code(code)
    return name, color, tcmarkers.HU

def draw_chart():
    print(f"[{time.strftime('%H:%M:%S')}] 正在從 GitHub Pages 下載數據並生成預報圖 ({TC_NAME})...")
    
    try:
        # 從 GitHub Pages 讀取 CSV
        df_past = pd.read_csv(PAST_CSV_URL)
        df_fore = pd.read_csv(FORE_CSV_URL)
        
        # 過去資料：優先用 intensity 欄位，否則從風速推算
        past_data = []
        for _, row in df_past.iterrows():
            if 'intensity' in df_past.columns and pd.notna(row.get('intensity')):
                code = str(row['intensity']).strip().upper()
            else:
                code = get_intensity_code(row['wind'], row.get('type', 'tropical'))
            past_data.append([row['datetime'], row['lng'], row['lat'], row['wind'], row['minimum central pressure'], code])
        
        curr = past_data[-1]
        
        # 預報資料：優先用 intensity 欄位，否則從風速推算
        forecast_data = []
        for _, row in df_fore.iterrows():
            h = int(str(row['f_time']).replace('hr', ''))
            if 'intensity' in df_fore.columns and pd.notna(row.get('intensity')):
                int_code = str(row['intensity']).strip().upper()
            else:
                int_code = get_intensity_code(row['wind'], row.get('type', 'tropical'))
            forecast_data.append([
                row['f_time'], row['lng'], row['lat'], row['wind'], h,
                row['minimum central pressure'], row.get('type', 'tropical'), int_code
            ])

        # 畫布整體放大
        fig, ax = plt.subplots(figsize=(14, 12), subplot_kw={'projection': ccrs.PlateCarree()})
        
        # 畫布背景純白
        fig.patch.set_facecolor("#FFFFFF")   
        
        # 邊界
        lon_min, lon_max, lat_min, lat_max = 100.0, 160.0, 7.5, 52.5
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

        # ==================== 2. 地圖美化配色（柔和高質感） ====================
        ax.set_facecolor("#C7DDF0")  # 海洋底色
        ax.add_feature(cfeature.OCEAN, facecolor="#C7DDF0", zorder=0)                      
        ax.add_feature(cfeature.LAND, facecolor="#F4EFE2", edgecolor="#9DB0BA", 
                       linewidth=0.6, zorder=1)                                            
        ax.add_feature(cfeature.COASTLINE, linewidth=0.85, edgecolor='#7A8C96', zorder=2)  
        ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5, 
                       edgecolor='#B5C2CB', zorder=2)                                       

        gl = ax.gridlines(draw_labels=True, linewidth=0.4, color='#A8B8C0', 
                          alpha=0.45, linestyle='--', zorder=1)
        gl.top_labels = gl.right_labels = False
        gl.xlocator = mticker.MultipleLocator(5)
        gl.ylocator = mticker.MultipleLocator(5)
        gl.xlabel_style = {'color': '#5A6B75', 'fontsize': 10}
        gl.ylabel_style = {'color': '#5A6B75', 'fontsize': 10}

        # ==================== 3. 標記澳門與香港位置 ====================
        ax.plot(MACAO_LON, MACAO_LAT, '*', color="#00A896", ms=13.0, 
                mec='#00695C', mew=1.0, zorder=12)
        ax.plot(HK_LON, HK_LAT, '*', color="#E63946", ms=13.0, 
                mec='#9B1D20', mew=1.0, zorder=12)

        # ==================== 4. 路徑與預報區域繪製 ====================
        # 過去路徑線
        ax.plot([d[1] for d in past_data], [d[2] for d in past_data], 
                color="#0A8C10", lw=2.8, solid_capstyle='round', zorder=4)
        
        # 預報誤差扇形/橢圓區域
        f_hs = [d[4] for d in forecast_data]
        all_h, all_ln, all_lt = [0] + f_hs, [curr[1]] + [d[1] for d in forecast_data], [curr[2]] + [d[2] for d in forecast_data]
        all_er = [0] + [((h // 24) * 100 + (h % 24) * (100 / 24)) * (1 / 111) for h in f_hs]
        ih = np.linspace(0, max(all_h), 100)
        xi, yi, ri = PchipInterpolator(all_h, all_ln)(ih), PchipInterpolator(all_h, all_lt)(ih), PchipInterpolator(all_h, all_er)(ih)
        ps = [Polygon(np.dstack((xi[i] + ri[i] * np.cos(np.linspace(0, 2 * np.pi, 360)), yi[i] + ri[i] * np.sin(np.linspace(0, 2 * np.pi, 360))))[0]) for i in range(len(ih))]
        
        # 誤差範圍
        ax.add_geometries([unary_union([MultiPolygon([ps[i], ps[i + 1]]).convex_hull for i in range(len(ps) - 1)])], 
                          ccrs.PlateCarree(), fc="#DCE5EC", alpha=0.55, ec="#90A4AE", lw=1.0, zorder=3)
        # 預報路徑
        ax.plot(xi, yi, color="#062FAD", lw=2.6, ls='--', zorder=4)

        # 預報點 ICON
        for d in forecast_data:
            _, ln, lt, wd, h, _, cyc, int_code = d
            _, col = get_intensity_by_code(int_code)
            if h in {24, 48, 72, 96, 120}:
                ax.plot(ln, lt, marker=tcmarkers.HU, ms=10.5, color=col, 
                        mec='#2C3E50', mew=0.8, zorder=10)

        # 現時位置 ICON
        _, c_col = get_intensity_by_code(curr[5])
        ax.plot(curr[1], curr[2], marker=tcmarkers.HU, ms=11.5, color=c_col, 
                mec='#2C3E50', mew=1.0, zorder=10)

        # ==================== 5. 標題與資訊欄 ====================
        fig.text(0.5, 0.96, f"熱帶氣旋「{TC_NAME}」路徑預報圖", ha='center', 
                 fontsize=26, fontweight='bold', color='#1F2D3D')
        fig.text(0.5, 0.92, f"預報時效：{max(f_hs)} 小時", ha='center', 
                 fontsize=18, color='#5A6B75')

        # 計算距離
        cyc_lon, cyc_lat = curr[1], curr[2]
        R = 6371.0

        def haversine(lon1, lat1, lon2, lat2):
            lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            return R * c

        dist_hk_km = haversine(cyc_lon, cyc_lat, HK_LON, HK_LAT)
        dist_macao_km = haversine(cyc_lon, cyc_lat, MACAO_LON, MACAO_LAT)
        dist_hk_rounded = round(dist_hk_km / 10) * 10
        dist_macao_rounded = round(dist_macao_km / 10) * 10

        # 整理預報資訊列表
        fore_info_lines = ["\n預報資訊："]
        
        try:
            if '/' in str(curr[0]) and ':' in str(curr[0]):
                base_time = datetime.datetime.strptime(str(curr[0]), '%d/%m/%Y %H:%M')
            else:
                base_time = pd.to_datetime(curr[0]).to_pydatetime()
        except Exception as e:
            print(f"時間解析失敗: {e}，使用當前系統時間替代")
            base_time = datetime.datetime.now()

        for d in forecast_data:
            if d[4] in {24, 48, 72, 96, 120}:
                f_h = d[4]
                fore_time = base_time + datetime.timedelta(hours=f_h)
                time_str = fore_time.strftime('%d/%m/%Y %H:%M')
                fore_info_lines.append(f"{time_str} {d[7]}")

        # 組合資訊欄文字
        info_txt = (f"現時資訊：\n"
                    f"距離澳門：{dist_macao_rounded}公里  距離香港：{dist_hk_rounded}公里\n"
                    f"{curr[0]}\n"
                    f"{curr[5]}, {curr[3]}kph, {curr[4]}hPa\n"
                    + "\n".join(fore_info_lines))
        
        # 資訊欄放大
        ax.text(0.03, 0.96, info_txt, transform=ax.transAxes, va='top', 
                fontsize=12.0, fontweight='bold', linespacing=1.6, color='#1F2D3D',
                bbox=dict(boxstyle="round,pad=0.6", fc="#FFFFFF", alpha=0.94, 
                          ec="#B0BEC5", lw=1.0), zorder=20)
        
        # ==================== 修改點：發佈單位字體放大 ====================
        ax.text(0.98, 0.98, "港澳天氣站HKMO_MET 發佈", transform=ax.transAxes, 
                ha='right', va='top', fontsize=18.0, fontweight='bold',
                color='#FFFFFF', 
                bbox=dict(boxstyle="round,pad=0.5", fc="#37474F", alpha=0.92, ec="none"), 
                zorder=20)

        # ==================== 6. 圖例整理 ====================
        leg_core_loc = [
            Line2D([0], [0], color="#388E3C", lw=2.5, solid_capstyle='round', label='過去路徑'), 
            Line2D([0], [0], color="#0288D1", lw=2.5, ls='--', label='預報路徑'), 
            plt.Rectangle((0, 0), 1, 1, fc="#DCE5EC", alpha=0.6, ec="#90A4AE", label='預報誤差範圍'),
            Line2D([0], [0], marker='*', color='w', markerfacecolor='#00A896', 
                   markeredgecolor='#00695C', ms=11.0, label='澳門'),
            Line2D([0], [0], marker='*', color='w', markerfacecolor='#E63946', 
                   markeredgecolor='#9B1D20', ms=11.0, label='香港')
        ]
        
        leg_int = [
            Line2D([0], [0], marker=tcmarkers.HU,
                   c=get_intensity_by_code(code)[1],
                   label=get_intensity_by_code(code)[0],
                   ms=7.0, mec='#2C3E50', mew=0.6, ls='')
            for code in ["LPA", "TD", "TS", "STS", "TY", "STY", "SUTY", "EX"]
        ]

        # ==================== 修改點：圖例聚攏（縮小間距） ====================
        leg_params = dict(
            loc='lower center', 
            frameon=True, 
            edgecolor='#CFD8DC', 
            facecolor="#FFFFFF", 
            framealpha=0.95,
            labelspacing=0.8,      
            handletextpad=1.0,     
            columnspacing=1.5,     
            borderpad=0.8          
        )

        fig.legend(handles=leg_core_loc, ncol=5, bbox_to_anchor=(0.5, 0.14), 
                   fontsize=14.0, markerscale=1.6, **leg_params)
        
        fig.legend(handles=leg_int, ncol=8, bbox_to_anchor=(0.5, 0.08), 
                   fontsize=14.0, markerscale=1.6, **leg_params)

        plt.subplots_adjust(bottom=0.22, top=0.90)
        
        plt.savefig(OUTPUT_IMG, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()
        
        print(f"[{time.strftime('%H:%M:%S')}] √ 預報圖生成成功 ({OUTPUT_IMG})")

    except Exception as e: 
        print(f"[{time.strftime('%H:%M:%S')}] × 讀取或繪圖失敗: {e}")

if __name__ == "__main__":
    draw_chart()