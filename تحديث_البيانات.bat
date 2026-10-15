@echo off
chcp 65001 > nul
title تحديث بيانات إنتاجية قسم المعادن - Metals Dashboard

echo ====================================================================
echo        تحديث بيانات قسم المعادن (Metals Department Dashboard)
echo ====================================================================
echo.
echo  1. تحديث البيانات محلياً فقط
echo  2. تحديث البيانات والرفع التلقائي إلى GitHub (أونلاين)
echo.
set /p opt="اختر رقم العملية (1 أو 2) [الافتراضي: 2]: "

if "%opt%"=="1" (
    echo.
    echo جاري التحديث المحلي...
    python update_daily_data.py %*
) else (
    echo.
    echo جاري التحديث والرفع إلى GitHub...
    python update_daily_data.py --push %*
)

echo.
echo ====================================================================
echo اضغط أي مفتاح للإغلاق...
pause > nul
