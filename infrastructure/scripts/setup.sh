#!/bin/bash

echo "🚀 Setting up CloudIntelligence development environment..."

# Create .env files
echo "Creating environment files..."
cat > backend/.env << EOF
# Application
SECRET_KEY=$(openssl rand -hex 32)
ENVIRONMENT=development
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://cloudintel:cloudintel_pass@localhost:5432/cloudintel

# Redis
REDIS_URL=redis://localhost:6379/0

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=cloudintel_pass

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# CORS
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
EOF

cat > frontend/.env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF

echo "✅ Environment files created"

# Install dependencies
echo "Installing Python dependencies..."
cd backend
pip install -r requirements.txt

echo "Installing Node.js dependencies..."
cd ../frontend
npm install

echo "Starting services with Docker Compose..."
cd ../infrastructure
docker-compose up -d

echo "🎉 Setup complete!"
echo ""
echo "Services running:"
echo "  • Frontend: http://localhost:3000"
echo "  • Backend API: http://localhost:8000"
echo "  • API Docs: http://localhost:8000/docs"
echo "  • Neo4j Browser: http://localhost:7474"
echo ""
echo "To stop services: docker-compose down"