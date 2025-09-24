# Care Count - Deployment Quick Reference

## 🚀 Quick Commands

### Start the App
```bash
streamlit run streamlit_app.py
```
**Access at:** http://localhost:8501

### Test the App
```bash
# Run all tests
python test_app.py test

# Create backup
python test_app.py backup "description"

# Restore from backup
python test_app.py restore backup_name
```

### Deploy Modern UI
```bash
# Deploy with testing
python deploy_modern.py deploy

# List backups
python deploy_modern.py list

# Rollback
python deploy_modern.py rollback backup_name

# Test only
python deploy_modern.py test
```

## 📁 Important Files

| File | Purpose |
|------|---------|
| `streamlit_app.py` | Main app (now modern version) |
| `streamlit_app_modern.py` | Modern UI source |
| `ui_improvements.py` | UI component library |
| `test_app.py` | Testing framework |
| `deploy_modern.py` | Deployment script |
| `.streamlit/secrets.toml` | Configuration |
| `backups/` | Automatic backups |

## 🔧 Configuration

### Required Secrets
```toml
# .streamlit/secrets.toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
```

### Optional Configuration
```toml
APP_TZ = "America/Toronto"
CUTOFF_HOUR = "20"
INACTIVITY_MIN = "30"
PROVIDER = "nebius"
GEMMA_MODEL = "google/gemma-3-27b-it"
```

## 🧪 Testing Checklist

- [ ] App starts without errors
- [ ] Authentication flow works
- [ ] Visit management functions
- [ ] Item identification works
- [ ] Item logging functions
- [ ] Responsive design works
- [ ] All buttons and forms work

## 🚨 Troubleshooting

### App Won't Start
1. Check if port 8501 is free
2. Verify all dependencies installed
3. Check secrets configuration
4. Review error logs

### Authentication Issues
1. Verify Supabase URL and key
2. Check network connectivity
3. Review OTP email delivery
4. Check database permissions

### UI Issues
1. Clear browser cache
2. Check for JavaScript errors
3. Verify CSS loading
4. Test on different browsers

### Rollback Process
1. List available backups: `python deploy_modern.py list`
2. Rollback to previous version: `python deploy_modern.py rollback backup_name`
3. Verify app functionality
4. Check logs for issues

## 📊 Monitoring

### Log Files
- `care_count.log` - Application logs
- `test_results.log` - Test results
- `deployment.log` - Deployment logs
- `backups/deployment_log_*.json` - Deployment history

### Health Checks
- App accessible at http://localhost:8501
- All UI elements loading
- Database connectivity working
- AI services responding

## 🔄 Maintenance

### Daily
- Check app accessibility
- Review error logs
- Monitor performance

### Weekly
- Run comprehensive tests
- Review user feedback
- Check backup integrity

### Monthly
- Update dependencies
- Review security logs
- Performance optimization

## 📞 Emergency Procedures

### App Down
1. Check if process is running
2. Review error logs
3. Restart app: `streamlit run streamlit_app.py`
4. If issues persist, rollback to last working version

### Data Issues
1. Check database connectivity
2. Verify Supabase configuration
3. Review data integrity
4. Contact database administrator

### Security Concerns
1. Review access logs
2. Check for unauthorized access
3. Verify authentication flow
4. Update credentials if needed

---

**Remember:** Always create a backup before making changes!
