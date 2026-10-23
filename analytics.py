import logging
import asyncio
from datetime import datetime
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# Import admin components
from config import ADMIN_CHAT_ID, logger
from admin_handlers import get_db_connection # Import the PG connection function

def _get_daily_analytics_data() -> dict:
    """
    Synchronous DB query to get all daily stats.
    This runs in a separate thread.
    """
    
    query_stats = """
    SELECT
        (SELECT COUNT(*) FROM users WHERE first_seen::date = NOW()::date) AS new_users,
        (SELECT COUNT(DISTINCT user_id) FROM users WHERE last_seen::date = NOW()::date) AS active_users,
        (SELECT COUNT(*) FROM submissions WHERE created_at::date = NOW()::date) AS new_submissions,
        (SELECT COUNT(*) FROM submissions WHERE created_at::date = NOW()::date AND status = 'pending') AS pending_submissions
    ;
    """
    
    query_new_users_list = """
    SELECT first_name, last_name, username FROM users
    WHERE first_seen::date = NOW()::date
    ORDER BY first_seen;
    """
    
    report = {}
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Get the counts
                cursor.execute(query_stats)
                counts = cursor.fetchone()
                if counts:
                    report['new_users'] = counts[0]
                    report['active_users'] = counts[1]
                    report['new_submissions'] = counts[2]
                    report['pending_submissions'] = counts[3]
                else:
                    report.update({'new_users': 0, 'active_users': 0, 'new_submissions': 0, 'pending_submissions': 0})
                
                # Get the new user list
                cursor.execute(query_new_users_list)
                users = cursor.fetchall()
                report['user_list'] = users
        return report
    except Exception as e:
        logger.error(f"Failed to get daily analytics data from PG: {e}", exc_info=True)
        return {} # Return empty dict on error

async def daily_analytics_job(context: ContextTypes.DEFAULT_TYPE):
    """The job run by the JobQueue to send the daily analytics."""
    try:
        report_data = await asyncio.to_thread(_get_daily_analytics_data)
        
        if not report_data:
            raise Exception("Report data was empty.")
            
        date_str = datetime.now().strftime('%Y-%m-%d')
        message = f"📊 *Daily Analytics Report - {date_str}* 📈\n\n"
        
        message += f"👤 *User Activity*\n"
        message += f"  - New Users Today: *{report_data.get('new_users', 0)}*\n"
        message += f"  - Active Users Today: *{report_data.get('active_users', 0)}*\n\n"
        
        message += f"📝 *Submission Activity*\n"
        message += f"  - New Submissions Today: *{report_data.get('new_submissions', 0)}*\n"
        message += f"  - Pending Submissions: *{report_data.get('pending_submissions', 0)}*\n\n"
        
        message += "✨ *New Users List*\n"
        user_list = report_data.get('user_list', [])
        if not user_list:
            message += "- (No new users today)"
        else:
            for user in user_list:
                first, last, username = user
                name = first or ''
                if last:
                    name += f" {last}"
                username_str = f"(@{username})" if username else ""
                message += f"- {name.strip()} {username_str}\n"
        
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info("Daily analytics report sent successfully.")
        
    except Exception as e:
        logger.error(f"Failed to send daily analytics: {e}", exc_info=True)
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"Failed to generate daily analytics: {e}"
            )
        except Exception as e2:
            logger.error(f"Failed to even send analytics error message: {e2}")