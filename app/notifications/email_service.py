"""Email notification service"""
import logging
from datetime import datetime
from typing import List, Optional
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config.timezone import TimezoneConverter

logger = logging.getLogger(__name__)


class EmailNotificationService:
    """
    Email notification service using SMTP.
    
    Sends periodic summaries and error alerts via email.
    """
    
    def __init__(
        self,
        server: str,
        port: int,
        user: str,
        password: str,
        from_email: str,
        to_email: str,
        use_ssl: bool,
        timezone: str = "Africa/Johannesburg"
    ):
        """
        Initialize email service.
        
        Args:
            server: SMTP server
            port: SMTP port
            user: SMTP username
            password: SMTP password
            from_email: From email address
            to_email: To email address
            use_ssl: Use SSL connection
            timezone: Timezone for timestamp conversion
        """
        self.server = server
        self.port = port
        self.user = user
        self.password = password
        self.from_email = from_email
        self.to_email = to_email
        self.use_ssl = use_ssl
        self.tz_converter = TimezoneConverter(timezone)
    
    async def _send_email(self, subject: str, body: str) -> None:
        """
        Send email via SMTP.
        
        Args:
            subject: Email subject
            body: Email body (HTML)
        """
        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = self.from_email
            message['To'] = self.to_email
            
            html_part = MIMEText(body, 'html')
            message.attach(html_part)
            
            if self.use_ssl:
                await aiosmtplib.send(
                    message,
                    hostname=self.server,
                    port=self.port,
                    username=self.user,
                    password=self.password,
                    use_tls=True
                )
            else:
                await aiosmtplib.send(
                    message,
                    hostname=self.server,
                    port=self.port,
                    username=self.user,
                    password=self.password
                )
            
            logger.info(f"Email sent successfully: {subject}")
        
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
    
    async def send_summary_email(
        self,
        period_start: datetime,
        period_end: datetime,
        signals: List[dict],
        trades_opened: List[dict],
        trades_closed: List[dict],
        updates: List[dict],
        errors: List[dict]
    ) -> None:
        """
        Send periodic summary email.
        
        Args:
            period_start: Period start time
            period_end: Period end time
            signals: List of signals generated
            trades_opened: List of trades opened
            trades_closed: List of trades closed
            updates: List of SL/TP updates
            errors: List of errors
        """
        start_cat = self.tz_converter.format_local(period_start)
        end_cat = self.tz_converter.format_local(period_end)
        
        subject = f"Trading Scanner Summary: {start_cat} to {end_cat}"
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .error {{ color: red; }}
                .success {{ color: green; }}
            </style>
        </head>
        <body>
            <h1>Trading Scanner Summary</h1>
            <p><strong>Period:</strong> {start_cat} to {end_cat}</p>
            
            <h2>Signals Generated ({len(signals)})</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Direction</th>
                    <th>Entry</th>
                    <th>SL</th>
                    <th>TP</th>
                    <th>RR</th>
                </tr>
                {''.join([f"<tr><td>{s.get('symbol', 'N/A')}</td><td>{s.get('direction', 'N/A')}</td><td>{s.get('entry', 0):.2f}</td><td>{s.get('sl', 0):.2f}</td><td>{s.get('tp', 0):.2f}</td><td>{s.get('rr', 0):.2f}</td></tr>" for s in signals[:10]])}
            </table>
            
            <h2>Trades Closed ({len(trades_closed)})</h2>
            <table>
                <tr>
                    <th>Symbol</th>
                    <th>Direction</th>
                    <th>Result</th>
                    <th>R Multiple</th>
                </tr>
                {''.join([f"<tr><td>{t.get('symbol', 'N/A')}</td><td>{t.get('direction', 'N/A')}</td><td class=\"{'success' if t.get('result') == 'TP' else 'error'}\">{t.get('result', 'N/A')}</td><td>{t.get('r_multiple', 0):.2f}R</td></tr>" for t in trades_closed[:10]])}
            </table>
            
            <h2>SL/TP Updates ({len(updates)})</h2>
            <p>{len(updates)} updates made during this period.</p>
            
            <h2>Errors ({len(errors)})</h2>
            {''.join([f"<p class=\"error\"><strong>{e.get('component', 'Unknown')}:</strong> {e.get('message', 'No message')}</p>" for e in errors[:5]])}
            
            <hr>
            <p><em>This is an automated email from Trading Scanner Service</em></p>
        </body>
        </html>
        """
        
        await self._send_email(subject, body)
    
    async def send_error_email(
        self,
        component: str,
        severity: str,
        message: str,
        exception_type: str,
        symbol: Optional[str]
    ) -> None:
        """
        Send error alert email.
        
        Args:
            component: Component where error occurred
            severity: Error severity
            message: Error message
            exception_type: Exception type
            symbol: Symbol (if applicable)
        """
        timestamp_cat = self.tz_converter.format_local(datetime.utcnow())
        
        subject = f"[{severity}] Trading Scanner Error: {component}"
        
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                .error {{ color: red; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1 class="error">Trading Scanner Error Alert</h1>
            <p><strong>Time:</strong> {timestamp_cat}</p>
            <p><strong>Component:</strong> {component}</p>
            <p><strong>Severity:</strong> {severity}</p>
            <p><strong>Exception Type:</strong> {exception_type}</p>
            <p><strong>Symbol:</strong> {symbol if symbol else 'N/A'}</p>
            <hr>
            <h2>Error Message:</h2>
            <pre>{message}</pre>
            <hr>
            <p><em>This is an automated error alert from Trading Scanner Service</em></p>
        </body>
        </html>
        """
        
        await self._send_email(subject, body)
