#!/bin/bash
# 一键启动脚本

echo "=== 启动智能旅行助手 ==="

# 启动后端
echo "[1/2] 启动 FastAPI 后端..."
cd backend
pip install -r requirements.txt -q
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "后端 PID: $BACKEND_PID"

# 启动前端
echo "[2/2] 启动 Vue 前端..."
cd ../frontend
npm install
npm run dev &
FRONTEND_PID=$!
echo "前端 PID: $FRONTEND_PID"

echo ""
echo "=== 启动完成 ==="
echo "后端 API: http://localhost:8000"
echo "前端界面: http://localhost:5173"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止所有服务"

wait
