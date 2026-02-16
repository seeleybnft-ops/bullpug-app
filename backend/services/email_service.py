"""Email service using SendGrid."""

import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime, timezone
from ..utils.config import SENDGRID_API_KEY, SENDER_EMAIL

logger = logging.getLogger(__name__)


async def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send email via SendGrid."""
    if not SENDGRID_API_KEY:
        logger.warning("SendGrid API key not configured - email not sent")
        return False
    
    try:
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent to {to_email}, status: {response.status_code}")
        return response.status_code == 202
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


async def send_welcome_email(email: str, wallet_address: str) -> bool:
    """Send welcome email to new users."""
    html_content = f"""
    <html>
    <body style="font-family: 'Space Grotesk', Arial, sans-serif; background-color: #0A0A12; color: #fff; padding: 40px;">
        <div style="max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #0F0F1A 0%, #1A1A2E 100%); border-radius: 16px; padding: 40px; border: 1px solid rgba(0,255,163,0.2);">
            <img src="https://bullpug.com/wp-content/uploads/2024/10/04.10.2024_13.24.29_rec-1.png" alt="Bullpug" style="width: 80px; height: 80px; border-radius: 50%; margin-bottom: 20px;">
            <h1 style="color: #00FFA3; font-size: 28px; margin-bottom: 10px;">Welcome to Bullpug!</h1>
            <p style="color: #94a3b8; font-size: 16px; line-height: 1.6;">
                Your wallet <strong style="color: #fff;">{wallet_address[:8]}...{wallet_address[-4:]}</strong> has joined the Bullpug community!
            </p>
            <div style="background: rgba(0,255,163,0.1); border: 1px solid rgba(0,255,163,0.3); border-radius: 12px; padding: 20px; margin: 20px 0;">
                <h3 style="color: #00FFA3; margin-bottom: 10px;">What you can do:</h3>
                <ul style="color: #94a3b8; padding-left: 20px;">
                    <li>Play P2P betting games with real SOL</li>
                    <li>Compete in the Speed Run game leaderboard</li>
                    <li>Track your trades with the Trading Journal</li>
                    <li>Join the community forum discussions</li>
                </ul>
            </div>
            <a href="https://bullpug.com" style="display: inline-block; background: #00FFA3; color: #000; font-weight: bold; padding: 12px 24px; border-radius: 8px; text-decoration: none; margin-top: 20px;">
                Start Exploring
            </a>
            <p style="color: #64748b; font-size: 12px; margin-top: 30px;">
                Follow us: <a href="https://x.com/Bullpugcoin" style="color: #00FFA3;">@Bullpugcoin</a> | <a href="https://t.me/bullpugcoinchat" style="color: #00FFA3;">Telegram</a>
            </p>
        </div>
    </body>
    </html>
    """
    return await send_email(email, "Welcome to Bullpug - Guardian of the Memecoin Universe!", html_content)


async def send_weekly_summary_email(email: str, wallet_address: str, summary: dict) -> bool:
    """Send weekly performance summary email."""
    pnl_color = "#00FFA3" if summary.get('total_pnl', 0) >= 0 else "#FF4444"
    pnl_sign = "+" if summary.get('total_pnl', 0) >= 0 else ""
    
    html_content = f"""
    <html>
    <body style="font-family: 'Space Grotesk', Arial, sans-serif; background-color: #0A0A12; color: #fff; padding: 40px;">
        <div style="max-width: 600px; margin: 0 auto; background: linear-gradient(135deg, #0F0F1A 0%, #1A1A2E 100%); border-radius: 16px; padding: 40px; border: 1px solid rgba(0,255,163,0.2);">
            <img src="https://bullpug.com/wp-content/uploads/2024/10/04.10.2024_13.24.29_rec-1.png" alt="Bullpug" style="width: 60px; height: 60px; border-radius: 50%; margin-bottom: 20px;">
            <h1 style="color: #00FFA3; font-size: 24px; margin-bottom: 10px;">Your Weekly Summary</h1>
            <p style="color: #94a3b8; font-size: 14px;">Week ending {datetime.now(timezone.utc).strftime('%B %d, %Y')}</p>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 25px 0;">
                <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; text-align: center;">
                    <p style="color: #64748b; font-size: 12px; margin-bottom: 5px;">TOTAL P&L</p>
                    <p style="color: {pnl_color}; font-size: 24px; font-weight: bold;">{pnl_sign}${summary.get('total_pnl', 0):.2f}</p>
                </div>
                <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; text-align: center;">
                    <p style="color: #64748b; font-size: 12px; margin-bottom: 5px;">WIN RATE</p>
                    <p style="color: #00FFA3; font-size: 24px; font-weight: bold;">{summary.get('win_rate', 0):.1f}%</p>
                </div>
                <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; text-align: center;">
                    <p style="color: #64748b; font-size: 12px; margin-bottom: 5px;">TOTAL TRADES</p>
                    <p style="color: #fff; font-size: 24px; font-weight: bold;">{summary.get('total_trades', 0)}</p>
                </div>
                <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 20px; text-align: center;">
                    <p style="color: #64748b; font-size: 12px; margin-bottom: 5px;">BETS PLACED</p>
                    <p style="color: #D946EF; font-size: 24px; font-weight: bold;">{summary.get('bets_placed', 0)}</p>
                </div>
            </div>
            
            <a href="https://bullpug.com/journal" style="display: inline-block; background: #00FFA3; color: #000; font-weight: bold; padding: 12px 24px; border-radius: 8px; text-decoration: none;">
                View Full Journal
            </a>
            <p style="color: #64748b; font-size: 11px; margin-top: 30px;">
                To unsubscribe from weekly summaries, update your preferences in the app settings.
            </p>
        </div>
    </body>
    </html>
    """
    return await send_email(email, f"Bullpug Weekly Summary - {pnl_sign}${summary.get('total_pnl', 0):.2f}", html_content)
