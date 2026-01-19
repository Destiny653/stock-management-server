# Email Notification Setup

This application uses FastAPI-Mail to send email notifications. To enable email functionality, you need to configure your email settings.

## Configuration

Update the following environment variables in your `backend.env` or `.env` file:

```env
# Email Configuration
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=noreply@stockflow.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_FROM_NAME=StockFlow
MAIL_STARTTLS=True
MAIL_SSL_TLS=False
USE_CREDENTIALS=True
VALIDATE_CERTS=True
```

## Gmail Setup (Recommended for Testing)

If using Gmail:

1. Go to your Google Account settings
2. Enable 2-Factor Authentication
3. Generate an App Password:
   - Go to Security → 2-Step Verification → App passwords
   - Select "Mail" and your device
   - Copy the generated 16-character password
4. Use this app password as `MAIL_PASSWORD`

## Testing Notifications

The application provides test endpoints for each notification type:

### Test Push Notification
```bash
curl -X POST http://localhost:8000/api/v1/notifications/test/push-notification \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Low Stock Alert
```bash
curl -X POST http://localhost:8000/api/v1/notifications/test/low-stock-alert \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Order Update
```bash
curl -X POST http://localhost:8000/api/v1/notifications/test/order-update \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Test Weekly Report
```bash
curl -X POST http://localhost:8000/api/v1/notifications/test/weekly-report \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Notification Types

The system supports the following notification types:

1. **Push Notifications** - Sent when a user enables push notifications in their profile
2. **Low Stock Alerts** - Sent when product stock falls below reorder point
3. **Order Updates** - Sent when order status changes
4. **Weekly Reports** - Sent weekly with inventory summary

## User Preferences

Users can manage their notification preferences from their profile page:
- Email notifications
- Push notifications
- Low stock alerts
- Order updates
- Weekly reports

All preferences are stored in the user's profile and respected when sending notifications.
