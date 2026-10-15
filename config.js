// ===== Metals Department Dashboard Configuration =====
// إعدادات لوحة تحكم قسم المعادن - قابلة للتعديل بسهولة

// 1) قائمة الماكينات الأساسية لقسم المعادن (10 ماكينات)
const DEFAULT_MACHINES = [
    'RS01',
    'RS02',
    'RS03',
    'RS04',
    'RS05',
    'RS06',
    'CS01',
    'CS02',
    'DS01',
    'CN'
];

// 2) ماكينات البناشر (BN) - مخفية افتراضياً ويمكن للمستخدم إظهارها
const BUNCHER_MACHINES = [
    'BN01',
    'BN02',
    'BN06',
    'BN07',
    'BN08'
];

// 3) المستهدف اليومي القياسي (بالمتر في الـ 24 ساعة) لكل ماكينة
// المستهدف الإجمالي للفترة = المستهدف اليومي × عدد الأيام المميزة في الفترة المختارة
const MACHINE_DAILY_TARGETS = {
    'RS01': 30000,
    'RS02': 26000,
    'RS03': 30000,
    'RS04': 14000,
    'RS05': 26000,
    'RS06': 26000,
    'CS01': 30000,
    'CS02': 28000,
    'DS01': 90000,
    'CN':   26000
};

// 3) كارت معدلات السرعة والمستهدف اليومي حسب المقاس والخامة (بالمتر في 24 ساعة)
const RATE_TABLE = [
    // H12 / AL (ألومنيوم)
    { size: '16', rate_k: 80, target24h: 80000, material: 'AL' },
    { size: '25', rate_k: 90, target24h: 90000, material: 'AL' },
    { size: '35', rate_k: 110, target24h: 110000, material: 'AL' },
    { size: '50', rate_k: 26, target24h: 26000, material: 'AL' },
    { size: '70', rate_k: 26, target24h: 26000, material: 'AL' },
    { size: '75', rate_k: 26, target24h: 26000, material: 'AL' },
    { size: '78', rate_k: 26, target24h: 26000, material: 'AL' },
    { size: '95', rate_k: 26, target24h: 26000, material: 'AL' },
    { size: '120', rate_k: 28, target24h: 28000, material: 'AL' },
    { size: '150', rate_k: 36, target24h: 36000, material: 'AL' },
    { size: '185', rate_k: 36, target24h: 36000, material: 'AL' },
    { size: '240', rate_k: 30, target24h: 30000, material: 'AL' },
    { size: '300', rate_k: 26, target24h: 26000, material: 'AL' },
    { size: '400', rate_k: 26, target24h: 26000, material: 'AL' },
    { size: '500', rate_k: 25, target24h: 25000, material: 'AL' },
    { size: '630', rate_k: 20, target24h: 20000, material: 'AL' },
    { size: '800', rate_k: 15, target24h: 15000, material: 'AL' },
    { size: '1000', rate_k: 12, target24h: 12000, material: 'AL' },
    { size: '1200', rate_k: 18, target24h: 18000, material: 'AL' },
    { size: '1600', rate_k: 16, target24h: 16000, material: 'AL' },
    { size: '2000', rate_k: 14, target24h: 14000, material: 'AL' },

    // CU (نحاس)
    { size: '10', rate_k: 70, target24h: 70000, material: 'CU' },
    { size: '16', rate_k: 80, target24h: 80000, material: 'CU' },
    { size: '25', rate_k: 90, target24h: 90000, material: 'CU' },
    { size: '35', rate_k: 110, target24h: 110000, material: 'CU' },
    { size: '50', rate_k: 26, target24h: 26000, material: 'CU' },
    { size: '70', rate_k: 26, target24h: 26000, material: 'CU' },
    { size: '95', rate_k: 26, target24h: 26000, material: 'CU' },
    { size: '120', rate_k: 21, target24h: 21000, material: 'CU' },
    { size: '150', rate_k: 32, target24h: 32000, material: 'CU' },
    { size: '185', rate_k: 32, target24h: 32000, material: 'CU' },
    { size: '240', rate_k: 26, target24h: 26000, material: 'CU' },
    { size: '300', rate_k: 24, target24h: 24000, material: 'CU' },
    { size: '400', rate_k: 21, target24h: 21000, material: 'CU' },
    { size: '500', rate_k: 16, target24h: 16000, material: 'CU' },
    { size: '630', rate_k: 12, target24h: 12000, material: 'CU' },
    { size: '800', rate_k: 10, target24h: 10000, material: 'CU' },
    { size: '1000', rate_k: 7.5, target24h: 7500, material: 'CU' },
    { size: '1200', rate_k: 18, target24h: 18000, material: 'CU' },
    { size: '1600', rate_k: 16, target24h: 16000, material: 'CU' },
    { size: '2000', rate_k: 14, target24h: 14000, material: 'CU' }
];
