"""
Web Server for Portal Verification & Pakasir Webhook
=====================================================
Optional web server for portal-based verification and Pakasir payment webhooks.
"""

import asyncio
import logging
from aiohttp import web
from typing import Optional

from bot.config import config
from bot.services import db

logger = logging.getLogger(__name__)


class VerificationServer:
    """Web server for portal verification"""
    
    def __init__(self, bot_context=None):
        self.app = web.Application()
        self.bot_context = bot_context
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup web routes"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/verify', self.verify_page)
        self.app.router.add_post('/verify', self.verify_submit)
        self.app.router.add_get('/health', self.health_check)
        # Pakasir webhook endpoint
        self.app.router.add_post('/webhook/pakasir', self.pakasir_webhook)
    
    async def index(self, request: web.Request) -> web.Response:
        """Index page"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Safeguard Bot</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }
                .container {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 400px;
                    width: 100%;
                }
                .logo { font-size: 64px; margin-bottom: 20px; }
                h1 { color: #333; margin-bottom: 10px; }
                p { color: #666; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">🛡️</div>
                <h1>Safeguard Bot</h1>
                <p>Portal verifikasi untuk melindungi grup Telegram dari spam dan bot.</p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def verify_page(self, request: web.Request) -> web.Response:
        """Verification page"""
        token = request.query.get('token', '')
        chat_id = request.query.get('chat_id', '')
        user_id = request.query.get('user_id', '')
        
        if not all([token, chat_id, user_id]):
            return await self._error_page("Invalid verification link")
        
        # Check if verification exists
        try:
            pending = db.get_pending_verification(int(user_id), int(chat_id))
            if not pending:
                return await self._error_page("Verification not found or expired")
            
            if pending['answer'] != token:
                return await self._error_page("Invalid token")
        except:
            return await self._error_page("Invalid parameters")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Verify - Safeguard Bot</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }}
                .container {{
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 400px;
                    width: 100%;
                }}
                .logo {{ font-size: 64px; margin-bottom: 20px; }}
                h1 {{ color: #333; margin-bottom: 10px; }}
                p {{ color: #666; line-height: 1.6; margin-bottom: 30px; }}
                button {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 15px 40px;
                    font-size: 18px;
                    border-radius: 10px;
                    cursor: pointer;
                    transition: transform 0.2s, box-shadow 0.2s;
                }}
                button:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
                }}
                .loading {{ display: none; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">🔐</div>
                <h1>Verifikasi</h1>
                <p>Klik tombol di bawah untuk memverifikasi bahwa Anda bukan bot.</p>
                <form method="POST" id="verifyForm">
                    <input type="hidden" name="token" value="{token}">
                    <input type="hidden" name="chat_id" value="{chat_id}">
                    <input type="hidden" name="user_id" value="{user_id}">
                    <button type="submit" id="verifyBtn">✅ Saya Bukan Bot</button>
                </form>
            </div>
            <script>
                document.getElementById('verifyForm').onsubmit = function() {{
                    document.getElementById('verifyBtn').textContent = 'Memverifikasi...';
                    document.getElementById('verifyBtn').disabled = true;
                }};
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def verify_submit(self, request: web.Request) -> web.Response:
        """Handle verification submission"""
        try:
            data = await request.post()
            token = data.get('token', '')
            chat_id = int(data.get('chat_id', 0))
            user_id = int(data.get('user_id', 0))
            
            if not all([token, chat_id, user_id]):
                return await self._error_page("Missing parameters")
            
            # Verify
            pending = db.get_pending_verification(user_id, chat_id)
            if not pending:
                return await self._error_page("Verification not found or expired")
            
            if pending['answer'] != token:
                return await self._error_page("Invalid token")
            
            # Mark as verified in database
            db.verify_user(user_id, chat_id)
            db.delete_pending_verification(user_id, chat_id)
            db.increment_stat(chat_id, "verified")
            
            return await self._success_page()
            
        except Exception as e:
            return await self._error_page(f"Error: {str(e)}")
    
    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({"status": "ok"})
    
    async def pakasir_webhook(self, request: web.Request) -> web.Response:
        """
        Handle Pakasir payment webhook.
        
        Pakasir sends POST with JSON body:
        {
            "amount": 22000,
            "order_id": "240910HDE7C9",
            "project": "project_slug",
            "status": "completed",
            "payment_method": "qris",
            "completed_at": "2024-09-10T08:07:02.819+07:00"
        }
        """
        try:
            data = await request.json()
            
            logger.info(f"Received Pakasir webhook: {data}")
            
            order_id = data.get("order_id")
            amount = data.get("amount")
            status = data.get("status")
            project = data.get("project")
            completed_at = data.get("completed_at")
            
            if not all([order_id, amount, status]):
                logger.error(f"Invalid webhook data: {data}")
                return web.json_response({"error": "Invalid data"}, status=400)
            
            # Check if payment exists in database
            payment = db.get_pakasir_payment_by_order(order_id)
            if not payment:
                logger.warning(f"Payment not found for order: {order_id}")
                return web.json_response({"error": "Payment not found"}, status=404)
            
            # Verify amount matches
            if payment['amount'] != amount:
                logger.warning(f"Amount mismatch for order {order_id}: expected {payment['amount']}, got {amount}")
                return web.json_response({"error": "Amount mismatch"}, status=400)
            
            if status == "completed":
                # Update payment status
                db.update_pakasir_payment_status(order_id, 'completed', completed_at)
                
                # Check if this is a renewal
                from bot.services.pakasir import PREMIUM_PLANS_IDR
                
                is_renewal = db.has_previous_subscription(payment['user_id'])
                
                # Get plan info
                plan = PREMIUM_PLANS_IDR.get(payment['plan_type'])
                if plan:
                    # Create premium subscription
                    db.create_premium_subscription(
                        user_id=payment['user_id'],
                        plan_type=payment['plan_type'],
                        price_paid=payment['amount'],
                        duration_days=plan['duration_days'],
                        currency="IDR",
                        is_renewal=is_renewal
                    )
                    
                    logger.info(f"Premium activated for user {payment['user_id']} via webhook, order {order_id}")
                else:
                    logger.error(f"Invalid plan type: {payment['plan_type']}")
                    return web.json_response({"error": "Invalid plan"}, status=400)
            
            return web.json_response({"status": "ok"})
            
        except Exception as e:
            logger.error(f"Error processing Pakasir webhook: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def _error_page(self, message: str) -> web.Response:
        """Error page"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Error - Safeguard Bot</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }}
                .container {{
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 400px;
                    width: 100%;
                }}
                .logo {{ font-size: 64px; margin-bottom: 20px; }}
                h1 {{ color: #333; margin-bottom: 10px; }}
                p {{ color: #666; line-height: 1.6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">❌</div>
                <h1>Error</h1>
                <p>{message}</p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def _success_page(self) -> web.Response:
        """Success page"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Success - Safeguard Bot</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }
                .container {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 400px;
                    width: 100%;
                }
                .logo { font-size: 64px; margin-bottom: 20px; }
                h1 { color: #333; margin-bottom: 10px; }
                p { color: #666; line-height: 1.6; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">✅</div>
                <h1>Berhasil!</h1>
                <p>Verifikasi berhasil! Anda sekarang bisa mengirim pesan di grup.</p>
                <p style="margin-top: 20px;"><small>Anda dapat menutup halaman ini.</small></p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    def run(self, host: str = None, port: int = None):
        """Run the web server"""
        host = host or config.web_host
        port = port or config.web_port
        web.run_app(self.app, host=host, port=port)


def run_server():
    """Run the verification server standalone"""
    server = VerificationServer()
    print(f"Starting verification server on {config.web_host}:{config.web_port}")
    server.run()


if __name__ == "__main__":
    run_server()
