import time
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy.interpolate import PchipInterpolator
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from matplotlib.lines import Line2D
import tcmarkers




# ==================== 1. 氣旋與 GitHub Pages 網址設定 ====================
TC_ID = "A"
TC_NAME = "未命名"




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




def get_intensity_info(wind, cyc_type="tropical"):
    if cyc_type == "EX": return "溫帶氣旋", "#BDBDBD", tcmarkers.HU
    if wind < 41: return "低壓區", "#BDBDBD", tcmarkers.HU
    elif 41 <= wind <= 62: return "熱帶低氣壓", "#FFF176", tcmarkers.HU
    elif 63 <= wind <= 87: return "熱帶風暴", "#64B5F6", tcmarkers.HU
    elif 88 <= wind <= 117: return "強烈熱帶風暴", "#4CAF50", tcmarkers.HU
    elif 118 <= wind <= 149: return "颱風", "#FFB74D", tcmarkers.HU
    elif 150 <= wind <= 184: return "強颱風", "#FF7043", tcmarkers.HU
    else: return "超強颱風", "#BA68C8", tcmarkers.HU




def draw_chart():
    print(f"[{time.strftime('%H:%M:%S')}] 正在從 GitHub Pages 下載數據並生成預報圖 ({TC_NAME})...")
    
    try:
        # 從 GitHub Pages 讀取 CSV
        df_past = pd.read_csv(PAST_CSV_URL)
        df_fore = pd.read_csv(FORE_CSV_URL)
        
        past_data = df_past[['datetime', 'lng', 'lat', 'wind', 'minimum central pressure']].values.tolist()
        curr = past_data[-1]
        
        forecast_data = []
        for _, row in df_fore.iterrows():
            h = int(str(row['f_time']).replace('hr', ''))
            forecast_data.append([row['f_time'], row['lng'], row['lat'], row['wind'], h, row['minimum central pressure'], row.get('type', 'tropical')])




        fig, ax = plt.subplots(figsize=(12, 10), subplot_kw={'projection': ccrs.PlateCarree()})
        
        # 根據過去與預報經緯度動態或固定邊界
        lon_min, lon_max, lat_min, lat_max = 105.0, 122.5, 15.5, 30.5
        ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())




        # ==================== 2. 地圖美化配色 ====================
        ax.add_feature(cfeature.LAND, facecolor="#F4F1EA", edgecolor="#A0AAB2", linewidth=0.6, zorder=1)
        ax.add_feature(cfeature.OCEAN, facecolor="#DCE8F5", zorder=0)
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor='#455A64', zorder=2)
        ax.add_feature(cfeature.BORDERS, linestyle=':', linewidth=0.5, edgecolor='#90A4AE', zorder=2)




        gl = ax.gridlines(draw_labels=True, linewidth=0.4, color='#90A4AE', alpha=0.5, linestyle='--', zorder=1)
        gl.top_labels = gl.right_labels = False
        gl.xlocator = mticker.MultipleLocator(5)
        gl.ylocator = mticker.MultipleLocator(5)




        # ==================== 3. 標記澳門與香港位置 ====================
        ax.plot(MACAO_LON, MACAO_LAT, '*', color="#00897B", ms=8.0, mec='#004D40', mew=0.8, zorder=12)
        ax.plot(HK_LON, HK_LAT, '*', color="#E53935", ms=8.0, mec='#880E4F', mew=0.8, zorder=12)




        # ==================== 4. 路徑與預報區域繪製 ====================
        # 過去路徑線
        ax.plot([d[1] for d in past_data], [d[2] for d in past_data], color="#2E7D32", lw=2.4, zorder=4)
        
        # 預報誤差扇形/橢圓區域
        f_hs = [d[4] for d in forecast_data]
        all_h, all_ln, all_lt = [0] + f_hs, [curr[1]] + [d[1] for d in forecast_data], [curr[2]] + [d[2] for d in forecast_data]
        all_er = [0] + [((h // 24) * 100 + (h % 24) * (100 / 24)) * (1 / 111) for h in f_hs]
        ih = np.linspace(0, max(all_h), 100)
        xi, yi, ri = PchipInterpolator(all_h, all_ln)(ih), PchipInterpolator(all_h, all_lt)(ih), PchipInterpolator(all_h, all_er)(ih)
        ps = [Polygon(np.dstack((xi[i] + ri[i] * np.cos(np.linspace(0, 2 * np.pi, 360)), yi[i] + ri[i] * np.sin(np.linspace(0, 2 * np.pi, 360))))[0]) for i in range(len(ih))]
        ax.add_geometries([unary_union([MultiPolygon([ps[i], ps[i + 1]]).convex_hull for i in range(len(ps) - 1)])], 
                          ccrs.PlateCarree(), fc="#FFF3E0", alpha=0.40, ec="#FFB74D", lw=0.8, zorder=3)
        ax.plot(xi, yi, color="#0288D1", lw=2.2, ls='--', zorder=4)




        # 預報點 ICON（縮小至 ms=6.0，12hr 節點 ms=4.0）
        for d in forecast_data:
            _, ln, lt, wd, h, _, cyc = d
            _, col, m = get_intensity_info(wd, cyc)
            if h in {24, 48, 72, 96, 120}:
                ax.plot(ln, lt, marker=m, ms=7.0, color=col, mec='k', mew=0.6, zorder=10)
            else:
                ax.plot(ln, lt, marker='x', ms=5.0, color="#0288D1", mew=0.8, zorder=9)




        # 現時位置 ICON（縮小至 ms=7.5）
        _, c_col, c_m = get_intensity_info(curr[3])
        ax.plot(curr[1], curr[2], marker=c_m, ms=7.5, color=c_col, mec='k', mew=0.8, zorder=10)




        # ==================== 5. 標題與資訊欄 ====================
        fig.text(0.5, 0.94, f"熱帶氣旋 “{TC_NAME}” 路徑預報圖", ha='center', fontsize=20, fontweight='bold', color='#263238')
        #fig.text(0.5, 0.94, f"南海中部潛在熱帶氣旋 路徑預報圖", ha='center', fontsize=20, fontweight='bold', color='#263238')
        fig.text(0.5, 0.91, f"預報時效：{max(f_hs)} 小時", ha='center', fontsize=13, color='#546E7A')



        # 計算距離，使用 Haversine 球面公式，與前端 turf.js 算法一致
        cyc_lon, cyc_lat = curr[1], curr[2]
        R = 6371.0  # 地球半徑 km


        def haversine(lon1, lat1, lon2, lat2):
            lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
            c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
            return R * c


        dist_hk_km = haversine(cyc_lon, cyc_lat, HK_LON, HK_LAT)
        dist_macao_km = haversine(cyc_lon, cyc_lat, MACAO_LON, MACAO_LAT)
        # 捨入至最近10公里 → XX0
        dist_hk_rounded = round(dist_hk_km / 10) * 10
        dist_macao_rounded = round(dist_macao_km / 10) * 10



        info_txt = (f"現時位置資料\n時間：{curr[0]}\n強度：{get_intensity_info(curr[3])[0]}\n"
                    f"近中心最大風速：{curr[3]}kph  中心氣壓：{curr[4]}hPa\n"
                    f"現時位置：{curr[2]:.1f}°N, {curr[1]:.1f}°E\n"
                    f"距香港：{dist_hk_rounded}公里  距澳門：{dist_macao_rounded}公里")
        ax.text(0.03, 0.96, info_txt, transform=ax.transAxes, va='top', fontsize=9.0, fontweight='bold', linespacing=1.35,
                bbox=dict(boxstyle="round,pad=0.4", fc="white", alpha=0.88, ec="#B0BEC5", lw=0.8), zorder=20)
        
        # 修改發佈單位
        ax.text(0.98, 0.98, "港澳天氣站發佈", transform=ax.transAxes, ha='right', va='top', fontsize=11.0, fontweight='bold',
                color='#263238', bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.9, ec="none"), zorder=20)




        # ==================== 6. 圖例整理 ====================
        leg_core_loc = [
            Line2D([0], [0], color="#2E7D32", lw=2.2, label='過去路徑'), 
            Line2D([0], [0], color="#0288D1", lw=2.2, ls='--', label='預報路徑'), 
            plt.Rectangle((0, 0), 1, 1, fc="#FFF3E0", alpha=0.5, ec="#FFB74D", label='預報誤差範圍'),
            Line2D([0], [0], marker='*', color='w', markerfacecolor='#00897B', markeredgecolor='#004D40', ms=8.5, label='澳門'),
            Line2D([0], [0], marker='*', color='w', markerfacecolor='#E53935', markeredgecolor='#880E4F', ms=8.5, label='香港')
        ]
        
        # 強度圖例標記放大 ms=4.0 → ms=5.2
        leg_int = [Line2D([0], [0], marker=tcmarkers.HU, c=get_intensity_info(v)[1], label=get_intensity_info(v)[0], ms=5.2, mec='k', mew=0.5, ls='') for v in [30, 50, 75, 100, 130, 160, 200]]
        
        leg_node = [
            Line2D([0], [0], marker=tcmarkers.HU, color="#0288D1", ms=5.2, mec='#333', mew=0.5, ls='', label='24小時預報節點'), 
            Line2D([0], [0], marker='x', color="#0288D1", ms=4.2, mew=0.8, ls='', label='12小時預報節點')
        ]




        leg_params = dict(loc='lower center', frameon=True, edgecolor='#CFD8DC', facecolor='white', framealpha=0.90)

        # 圖例字體放大：8.5 → 9.5；8.0 → 9.0；8.5 →9.5
        fig.legend(handles=leg_core_loc, ncol=5, bbox_to_anchor=(0.5, 0.13), fontsize=9.5, **leg_params)
        fig.legend(handles=leg_int, ncol=7, bbox_to_anchor=(0.5, 0.08), fontsize=9.0, **leg_params)
        fig.legend(handles=leg_node, ncol=2, bbox_to_anchor=(0.5, 0.04), fontsize=9.5, **leg_params)




        plt.subplots_adjust(bottom=0.2, top=0.88)
        plt.savefig(OUTPUT_IMG, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"[{time.strftime('%H:%M:%S')}] √ 預報圖生成成功 ({OUTPUT_IMG})")




    except Exception as e: 
        print(f"[{time.strftime('%H:%M:%S')}] × 讀取或繪圖失敗: {e}")




if __name__ == "__main__":
    draw_chart()
