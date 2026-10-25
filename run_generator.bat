@echo off
chcp 65001 >nul
cd /d "d:\计算机毕业设计\医疗疾病系统"
".venv\Scripts\python.exe" generate_medical_data.py
echo.
echo 执行完成！
pause
