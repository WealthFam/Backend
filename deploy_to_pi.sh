#!/bin/bash

# Configuration
REMOTE_USER="root"
REMOTE_HOST="192.168.0.7"
REMOTE_DIR="~/wealthfam"
ARCHIVE_NAME="wealthfam_deploy.tar.gz"

# Read version from version.json
MAJOR=$(grep -oP '"major": \K\d+' version.json)
MINOR=$(grep -oP '"minor": \K\d+' version.json)
PATCH=$(grep -oP '"patch": \K\d+' version.json)
VERSION="$MAJOR.$MINOR.$PATCH"

# Generate build string: master hash-date (e.g., c196-20260124)
GIT_HASH=$(git rev-parse master 2>/dev/null | cut -c1-4 || echo "0000")
BUILD_DATE=$(date +%Y%m%d)
BUILD_NUM="$GIT_HASH-$BUILD_DATE"

echo "📦 Packaging WealthFam v$VERSION (Build: $BUILD_NUM)..."

# Create a temporary staging directory
STAGING_DIR=".deploy_staging"
rm -rf $STAGING_DIR
mkdir -p $STAGING_DIR

# Copy files to staging (using rsync if available would be better, but cp -r works)
# We handle exclusions by just copying what we need or removing after
cp -r backend $STAGING_DIR/
cp -r frontend $STAGING_DIR/
cp -r parser $STAGING_DIR/
cp -r scripts $STAGING_DIR/
cp Dockerfile $STAGING_DIR/
cp docker-compose.yml $STAGING_DIR/
cp entrypoint.sh $STAGING_DIR/
cp build_and_push.sh $STAGING_DIR/
cp run_backend.py $STAGING_DIR/
cp version.json $STAGING_DIR/
# Create data dir structure
mkdir -p $STAGING_DIR/data
touch $STAGING_DIR/data/.gitkeep

# Clean up unnecessary files in staging
rm -rf $STAGING_DIR/frontend/node_modules
rm -rf $STAGING_DIR/backend/__pycache__
find $STAGING_DIR -name "*.pyc" -delete

# Local conversion removed in favor of remote sanitization

# Create archive from staging
tar -czf "$ARCHIVE_NAME" -C $STAGING_DIR .

# Clean up staging
rm -rf $STAGING_DIR

if [ $? -eq 0 ]; then
    echo "✅ Archive created: $ARCHIVE_NAME"
    
    echo "🚀 Uploading to $REMOTE_USER@$REMOTE_HOST..."
    # Ensure remote directory exists and upload
    ssh $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_DIR"
    scp $ARCHIVE_NAME $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/
    
    if [ $? -eq 0 ]; then
        # Extract AND fix line endings.
        # CRITICAL: We completely recreate entrypoint.sh to ensure no BOM/CRLF issues persist.
        ssh $REMOTE_USER@$REMOTE_HOST "cd $REMOTE_DIR && \
        tar -xzf $ARCHIVE_NAME && \
        rm $ARCHIVE_NAME && \
        find . -name '*.sh' -exec sed -i 's/\r$//' {} + && \
        printf '#!/bin/bash\npython scripts/recover_db.py\npython scripts/vacuum_db.py\nnginx\npython run_backend.py\n' > entrypoint.sh && \
        chmod +x *.sh"
        
        echo "✨ Deployment successful!"
        echo "To run the app on your Pi, SSH into it and run:"
        echo "cd $REMOTE_DIR && VITE_APP_BUILD=$BUILD_NUM docker-compose down && VITE_APP_BUILD=$BUILD_NUM TAG=latest docker-compose up -d --build --force-recreate"
    else
        echo "❌ Upload failed!"
    fi
    
    # Cleanup local archive
    rm $ARCHIVE_NAME
else
    echo "❌ Packaging failed!"
    exit 1
fi
