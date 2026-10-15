# -*- coding: utf-8 -*-
"""
update_daily_data.py
====================
سكريبت التحديث التلقائي لبيانات قسم المعادن (Metals Department Dashboard)
يقوم بقراءة أي ملف تصدير جديد (Orders_Export_*.csv أو .xlsx)
واستخراج ماكينات قسم المعادن (10 ماكينات: RS01-RS06, CS01, CS02, DS01, CN)
ودمجها مع قاعدة البيانات metals_data.json وتحديث نسخة الكاش في index.html
مع إمكانية الرفع المباشر إلى GitHub.

الاستخدام:
  python update_daily_data.py [اسم_الملف] [--push]
أو بمجرد تشغيل:
  python update_daily_data.py
حيث سيقوم تلقائياً باكتشاف أحدث ملف تصدير في المجلد.
"""

import os
import sys
import glob
import json
import re
import datetime
import subprocess

# ضمان دعم الترميز على كونسول ويندوز
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# خريطة الماكينات العشر لقسم المعادن
MACHINE_ID_MAP = {
    '9': 'RS01',
    '10': 'RS02',
    '11': 'RS03',
    '12': 'RS04',
    '13': 'RS05',
    '14': 'RS06',
    '15': 'CS01',
    '16': 'CS02',
    '17': 'DS01',
    '18': 'CN'
}

CORE_MACHINES = set(MACHINE_ID_MAP.values())
ALLOWED_MACHINE_IDS = set(MACHINE_ID_MAP.keys())

# العملاء المعروفين بحسب بادئة أمر الشغل
PREFIX_CUSTOMERS = {
    '1279/25': 'Energya Stock',
    '1385/26': 'السويدي اليكتريك',
    '1713/26': 'VLG RO S.R.L.',
    '177/26': 'Faber Kabel',
    '1778/26': 'Faber Kabel',
    '1789/26': 'Mehta Electricals - Kenya',
    '1868/26': 'السويدي كابلز',
    '1872/26': 'السويدي كابلز',
    '809/26': 'السويدي كابلز',
    '1101/26': 'Energya Cables',
    '1264/26': 'Energya Cables',
    '1446/26': 'Energya Cables',
    '1547/26': 'Energya Cables',
    '1553/26': 'Energya Cables',
    '1594/26': 'Energya Cables',
    '1745/26': 'Energya Cables',
    '1772/26': 'Energya Cables'
}

def clean_wire_size(raw_size):
    """تنظيف وتوحيد مقاس السلك/الموصل"""
    s = str(raw_size or '').strip()
    if not s or s in ('-', 'nan', 'None'):
        return '-'
    s = s.replace('MM2', '').replace('mm2', '').replace('Mm2', '').strip()
    if '+' in s:
        s = s.split('+')[0].strip()
    if '/' in s:
        s = s.split('/')[0].strip()
    s = s.replace('*', 'x').replace('X', 'x')
    parts = [p.strip() for p in s.split('x') if p.strip()]
    return parts[-1] if parts else s

def load_metadata_maps():
    """تحميل جداول البيانات الوصفية من wip002_pr.xls و wip001_pp.xls إذا كانت متوفرة"""
    wip2_map = {}
    if os.path.exists('wip002_pr.xls'):
        try:
            import pandas as pd
            df2 = pd.read_excel('wip002_pr.xls')
            for _, r in df2.iterrows():
                wo = str(r.get('workorder', '')).strip()
                if wo and wo not in wip2_map:
                    wip2_map[wo] = {
                        'cable': str(r.get('cable', '')).strip(),
                        'familyid': str(r.get('familyid', '')).strip().upper(),
                        'customer': str(r.get('customer', '')).strip(),
                        'joborder': str(r.get('joborder', '')).strip()
                    }
        except Exception as e:
            print(f"[تحذير] تعذر قراءة wip002_pr.xls: {e}")

    wip1_map = {}
    if os.path.exists('wip001_pp.xls'):
        try:
            import pandas as pd
            df1 = pd.read_excel('wip001_pp.xls')
            for _, r in df1.iterrows():
                wo = str(r.get('wo', '')).strip()
                if wo and wo not in wip1_map:
                    cust = str(r.get('short_name', '')).strip()
                    if cust.lower() == 'nan':
                        cust = ''
                    wip1_map[wo] = {
                        'cable': str(r.get('ecblnm', '')).strip(),
                        'volt': str(r.get('volt', '')).strip(),
                        'customer': cust,
                        'joborder': str(r.get('job_no', '')).strip()
                    }
        except Exception as e:
            print(f"[تحذير] تعذر قراءة wip001_pp.xls: {e}")

    return wip2_map, wip1_map

def find_target_file(custom_arg=None):
    """تحديد ملف التصدير المستهدف"""
    if custom_arg and os.path.exists(custom_arg):
        return custom_arg

    # البحث عن أحدث ملف Orders_Export_*.csv أو .xlsx
    patterns = ['Orders_Export_*.csv', 'Orders_Export_*.xlsx', '*Orders*.csv', '*Orders*.xlsx', '*.csv']
    candidates = []
    for pat in patterns:
        for f in glob.glob(pat):
            if f.endswith('.py') or f.endswith('.json') or f == 'std.csv' or f == 'metal.csv':
                continue
            if os.path.isfile(f):
                candidates.append((os.path.getmtime(f), f))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]

def read_export_rows(filepath):
    """قراءة صفوف ملف التصدير سواء كان CSV أو Excel"""
    import pandas as pd
    print(f"📖 جاري قراءة الملف: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    df = None

    if ext == '.csv':
        encodings = ['utf-8', 'utf-8-sig', 'cp1256', 'latin1']
        for enc in encodings:
            try:
                df = pd.read_csv(filepath, dtype=str, keep_default_na=False, encoding=enc)
                break
            except Exception:
                continue
    elif ext in ('.xlsx', '.xls'):
        df = pd.read_excel(filepath, dtype=str)
        df.fillna('', inplace=True)
    else:
        raise ValueError(f"صيغة الملف غير مدعومة: {ext}")

    if df is None:
        raise ValueError("تعذر قراءة الملف بأي ترميز مدعوم.")

    # تنظيف أسماء الأعمدة
    df.columns = [str(c).strip() for c in df.columns]
    print(f"✅ تم تحميل {len(df)} صف من الملف بنجاح.")
    return df

def parse_and_extract_metals(df, wip2_map, wip1_map):
    """تصفية واستخراج ماكينات قسم المعادن وتوحيد البيانات"""
    records = []

    # تحديد الأعمدة بمرونة
    col_order = next((c for c in df.columns if c.lower() in ('orderid', 'order', 'wo', 'workorder')), 'OrderID')
    col_date = next((c for c in df.columns if c.lower() in ('regdate', 'date', 'pdate', 'prdate')), 'RegDate')
    col_shift = next((c for c in df.columns if c.lower() in ('shiftcode', 'shift', 'shift_code')), 'ShiftCode')
    col_machine = next((c for c in df.columns if c.lower() in ('machineid', 'machine', 'machine_id')), 'MachineID')
    col_len = next((c for c in df.columns if c.lower() in ('lengthmeters', 'length', 'packqty', 'len')), 'LengthMeters')
    col_wt = next((c for c in df.columns if c.lower() in ('weightton', 'weight', 'netwt', 'wt')), 'WeightTon')
    col_takeup = next((c for c in df.columns if c.lower() in ('takeupno', 'takeup', 'drumno', 'packno')), 'TakeUpNo')
    col_card = next((c for c in df.columns if c.lower() in ('receivecardno', 'cardno', 'label_no', 'label')), 'ReceiveCardNo')
    col_size = next((c for c in df.columns if c.lower() in ('wiresize', 'size', 'cablesize')), 'WireSize')
    col_mat = next((c for c in df.columns if c.lower() in ('conductormaterial', 'material')), 'ConductorMaterial')
    col_cu = next((c for c in df.columns if c.lower() in ('copperton', 'cu_ton')), 'CopperTon')

    filtered_count = 0
    dates_found = set()

    for _, row in df.iterrows():
        raw_m = str(row.get(col_machine, '')).strip()

        # هل تنتمي لماكينات المعادن؟
        machine_name = None
        if raw_m in MACHINE_ID_MAP:
            machine_name = MACHINE_ID_MAP[raw_m]
        elif raw_m.upper() in CORE_MACHINES:
            machine_name = raw_m.upper()

        if not machine_name:
            continue

        filtered_count += 1

        wo = str(row.get(col_order, '')).strip()
        raw_date = str(row.get(col_date, '')).strip()

        # توحيد صيغة التاريخ YYYY-MM-DD
        date_iso = ''
        if raw_date:
            raw_date = raw_date.split('T')[0].split(' ')[0]
            if '/' in raw_date:
                dp = raw_date.split('/')
                if len(dp) == 3:
                    if len(dp[0]) == 4:
                        date_iso = f"{dp[0]}-{int(dp[1]):02d}-{int(dp[2]):02d}"
                    elif len(dp[2]) == 4:
                        date_iso = f"{dp[2]}-{int(dp[1]):02d}-{int(dp[0]):02d}"
            elif '-' in raw_date:
                dp = raw_date.split('-')
                if len(dp) == 3:
                    if len(dp[0]) == 4:
                        date_iso = f"{dp[0]}-{int(dp[1]):02d}-{int(dp[2]):02d}"
                    elif len(dp[2]) == 4:
                        date_iso = f"{dp[2]}-{int(dp[1]):02d}-{int(dp[0]):02d}"

        if not date_iso:
            continue

        dates_found.add(date_iso)
        dp = date_iso.split('-')
        date_display = f"{dp[2]}/{dp[1]}/{dp[0]}"

        # الوردية
        raw_shift = str(row.get(col_shift, '')).strip().upper()
        if '1' in raw_shift:
            shift = '1'
        elif '2' in raw_shift:
            shift = '2'
        elif '3' in raw_shift:
            shift = '3'
        else:
            shift = '1'

        # الطول والوزن
        try:
            raw_len = float(row.get(col_len, 0) or 0)
            length = int(raw_len) if raw_len.is_integer() else round(raw_len, 2)
        except Exception:
            length = 0

        try:
            raw_wt = float(row.get(col_wt, 0) or 0)
            # إذا كان بالطن (أقل من 50 مثلاً) نحوله لكيلوجرام
            weight = round(raw_wt * 1000) if raw_wt < 100 else round(raw_wt)
        except Exception:
            weight = 0

        takeup = str(row.get(col_takeup, '')).strip()
        card_no = str(row.get(col_card, '')).strip() if col_card in row else ''
        size = clean_wire_size(row.get(col_size, ''))

        # الخامة
        mat_text = str(row.get(col_mat, '')).strip()
        cu_ton = 0.0
        try:
            cu_ton = float(row.get(col_cu, 0) or 0)
        except Exception:
            cu_ton = 0.0

        if 'نحاس' in mat_text or 'cu' in mat_text.lower() or cu_ton > 0:
            material = 'CU'
        else:
            material = 'AL'

        # جلب البيانات الوصفية من wip002 أو wip001
        lk2 = wip2_map.get(wo, {})
        lk1 = wip1_map.get(wo, {})

        # تصحيح بديل لأوامر محددة
        if not lk2 and not lk1 and wo == '177/26/10':
            lk2 = wip2_map.get('1778/26/10', {})
            lk1 = wip1_map.get('1778/26/10', {})

        cable = lk2.get('cable') or lk1.get('cable')
        if not cable or cable == 'nan' or (machine_name == 'DS01' and size == '50'):
            cable = f"0.6/1 KV,{material},1*{size}"

        familyid = lk2.get('familyid')
        if not familyid or familyid == 'nan':
            volt = lk1.get('volt', '')
            comb = (volt + ' ' + cable).upper()
            if any(v in comb for v in ['18/30', '12/20', '19/33', '25/44']):
                familyid = 'MV'
            elif any(v in comb for v in ['66KV', '132KV', '220KV']):
                familyid = 'HV'
            else:
                familyid = 'LV'

        customer = lk2.get('customer') or lk1.get('customer')
        if not customer or customer == 'nan' or not customer.strip():
            pfx = '/'.join(wo.split('/')[:2])
            customer = PREFIX_CUSTOMERS.get(pfx, '-')

        joborder = lk2.get('joborder') or lk1.get('joborder') or f"{wo}/STD/1"
        label_no = f"{wo}/STD/{card_no}" if card_no else f"{wo}/STD/{takeup}"

        # مشغل الماكينة
        raw_op = str(row.get('CreatedBy', '') or row.get('emp_name', '') or row.get('Operator', '') or '').strip()
        op_map = {
            'Ahmed Samy': 'أحمد سامي',
            'Mohamed hussein S': 'محمد حسين',
            'Mahmoud Mohamed Ahmed': 'محمود محمد أحمد',
            'Amr Ehab Fawzy': 'عمرو إيهاب فوزي',
            'Mohamed abdellatif Syam': 'محمد عبد اللطيف صيام',
            'mohamed Nasef': 'محمد ناصف'
        }
        operator = op_map.get(raw_op, raw_op)

        rec = {
            'workorder': wo,
            'joborder': joborder,
            'label_no': label_no,
            'cable': cable,
            'size': size,
            'material': material,
            'familyid': familyid,
            'drumno': takeup,
            'length': length,
            'weight': weight,
            'customer': customer,
            'shift': shift,
            'machine': machine_name,
            'dateIso': date_iso,
            'dateDisplay': date_display,
            'operator': operator
        }
        records.append(rec)

    print(f"🎯 تم استخراج {len(records)} أمر شغل يخص قسم المعادن عبر التواريخ: {sorted(list(dates_found))}")
    return records, dates_found

def merge_and_save_json(new_records, dates_to_replace, json_path='metals_data.json'):
    """دمج السجلات الجديدة مع قاعدة البيانات وحفظها"""
    existing_data = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        except Exception as e:
            print(f"[تحذير] خطأ في قراءة {json_path}: {e}")

    # حذف السجلات القديمة لنفس التواريخ الموجودة في ملف التصدير لتجنب التكرار
    cleaned_old = [r for r in existing_data if r.get('dateIso') not in dates_to_replace]
    print(f"📊 البيانات القديمة: {len(existing_data)} -> المتبقي بعد تنظيف التواريخ المحدثة: {len(cleaned_old)}")

    # دمج وترتيب
    combined = cleaned_old + new_records
    combined.sort(key=lambda r: (r.get('dateIso', ''), r.get('machine', ''), r.get('shift', '')))

    # إعادة ترقيم المعرف id
    for idx, r in enumerate(combined):
        r['id'] = idx + 1

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    # حفظ metals_data.js
    js_path = os.path.splitext(json_path)[0] + '.js'
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write('var METALS_DATA = ')
        json.dump(combined, f, ensure_ascii=False)
        f.write(';\nif (typeof window !== "undefined") { window.METALS_DATA = METALS_DATA; }\nif (typeof module !== "undefined" && module.exports) { module.exports = METALS_DATA; }\n')

    # تضمين البيانات مباشرة داخل ملف index.html ليعمل الداشبورد مستقلاً ويمكن رفعه منفرداً على GitHub
    embed_data_in_html(combined, html_path='index.html')

    print(f"💾 تم حفظ {len(combined)} سجل بنجاح في {json_path} و {js_path} و index.html!")
    return len(combined)

def embed_data_in_html(combined, html_path='index.html'):
    """تضمين البيانات بالكامل مباشرة داخل ملف index.html ليتمكن المستخدم من رفع ملف index.html بمفرده على GitHub وتحديث الداشبورد فوراً"""
    if not os.path.exists(html_path):
        return

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    json_str = json.dumps(combined, ensure_ascii=False)
    script_block = (
        '<script id="embeddedMetalsData">\n'
        f'var METALS_DATA = {json_str};\n'
        'if (typeof window !== "undefined") { window.METALS_DATA = METALS_DATA; }\n'
        'if (typeof module !== "undefined" && module.exports) { module.exports = METALS_DATA; }\n'
        '</script>'
    )

    if '<script id="embeddedMetalsData">' in content:
        content = re.sub(
            r'<script id="embeddedMetalsData">[\s\S]*?</script>',
            script_block,
            content
        )
    elif 'metals_data.js' in content:
        content = re.sub(
            r'<script src="metals_data\.js[^"]*"></script>',
            script_block,
            content
        )
    else:
        content = content.replace(
            '<script src="config.js',
            script_block + '\n    <script src="config.js'
        )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"📄 تم تحديث وتضمين كافة البيانات مباشرة داخل ملف {html_path} ({len(combined)} سجل)!")

def update_html_cache_buster(html_path='index.html'):
    """تحديث إصدار BUILD_VERSION وروابط الكاش في index.html لضمان التحديث الفوري عند المستخدمين"""
    if not os.path.exists(html_path):
        return

    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_version = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

    # تحديث BUILD_VERSION
    content = re.sub(
        r"const BUILD_VERSION\s*=\s*['\"][^'\"]+['\"];",
        f"const BUILD_VERSION = '{new_version}';",
        content
    )

    # تحديث query string لملفات config.js و metals_data.js و app.js
    content = re.sub(
        r'src="metals_data\.js\?v=[^"]*"',
        f'src="metals_data.js?v={new_version}"',
        content
    )
    content = re.sub(
        r'src="config\.js\?v=[^"]*"',
        f'src="config.js?v={new_version}"',
        content
    )
    content = re.sub(
        r'src="cable3d\.js\?v=[^"]*"',
        f'src="cable3d.js?v={new_version}"',
        content
    )
    content = re.sub(
        r'src="app\.js\?v=[^"]*"',
        f'src="app.js?v={new_version}"',
        content
    )

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"🚀 تم تحديث كاش المتصفح في {html_path} إلى الإصدار: {new_version}")

def git_commit_and_push():
    """الرفع التلقائي إلى مستودع GitHub"""
    try:
        print("\n🌐 جاري الرفع إلى GitHub...")
        subprocess.run(['git', 'add', 'metals_data.json', 'metals_data.js', 'index.html', 'app.js', 'styles.css', 'cable3d.js', 'three.bundle.min.js', 'update_daily_data.py'], check=True)
        commit_msg = f"Update metals daily data - {datetime.date.today().isoformat()}"
        subprocess.run(['git', 'commit', '-m', commit_msg], check=True)
        subprocess.run(['git', 'push', 'origin', 'main'], check=True)
        print("🎉 تم الرفع بنجاح إلى GitHub Pages!")
        print("🔗 الرابط المباشر: https://mahmoudshahin1.github.io/metals-dashboard/")
    except Exception as e:
        print(f"⚠️ تنبيه: تعذر الرفع المباشر عبر الأوامر (Git): {e}")
        print("💡 لا تقلق إطلاقاً! ملف index.html تم تحديثه محلياً بكامل البيانات الجديدة، ويمكنك رفعه مباشرة بيدك عبر موقع GitHub بالمتصفح ليتم التحديث أونلاين فوراً!")

def main():
    print("=" * 60)
    print("   تحديث بيانات قسم المعادن اليومية (Metals Dashboard)")
    print("=" * 60)

    # فحص المعاملات
    custom_file = None
    auto_push = False

    for arg in sys.argv[1:]:
        if arg == '--push':
            auto_push = True
        elif not arg.startswith('-') and custom_file is None:
            custom_file = arg

    target_file = find_target_file(custom_file)
    if not target_file:
        print("❌ لم يتم العثور على أي ملف تصدير جديد (Orders_Export_*.csv أو .xlsx).")
        print("يرجى وضع ملف اليوم الجديد في هذا المجلد ثم إعادة تشغيل السكريبت.")
        sys.exit(1)

    print(f"🎯 الملف المكتشف للتحديث: {target_file}")

    # 1. تحميل جداول البيانات الوصفية
    wip2_map, wip1_map = load_metadata_maps()

    # 2. قراءة الملف
    df = read_export_rows(target_file)

    # 3. استخراج ماكينات قسم المعادن وتوحيدها
    records, dates_found = parse_and_extract_metals(df, wip2_map, wip1_map)
    if not records:
        print("⚠️ لم يتم العثور على أي أوامر شغل لماكينات قسم المعادن في هذا الملف!")
        sys.exit(0)

    # 4. دمج وحفظ metals_data.json
    merge_and_save_json(records, dates_found)

    # 5. تحديث كاش index.html
    update_html_cache_buster()

    # 6. الرفع إلى GitHub
    if auto_push:
        git_commit_and_push()
    else:
        # سؤال المستخدم في بيئة التيرمينال
        if sys.stdin.isatty():
            choice = input("\nهل تريد رفع التحديثات مباشرة إلى GitHub الآن؟ (y/n) [default: y]: ").strip().lower()
            if choice in ('', 'y', 'yes'):
                git_commit_and_push()
        else:
            print("\n💡 لرفع التحديثات إلى GitHub، يمكنك تشغيل:")
            print("   python update_daily_data.py --push")

    print("\n✅ اكتمل التحديث بنجاح! شكراً لك.")

if __name__ == '__main__':
    main()
