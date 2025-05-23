"""
Simplified Combined Profile and Leaderboard Component.
"""

import streamlit as st
import logging
from typing import Dict, Any, List
from auth.badge_manager import BadgeManager
from utils.language_utils import t, get_current_language

logger = logging.getLogger(__name__)

class ProfileLeaderboardSidebar:
    """Simplified combined profile and leaderboard sidebar component."""
    
    def __init__(self):
        self.badge_manager = BadgeManager()
    
    def render_combined_sidebar(self, user_info: Dict[str, Any], user_id: str) -> None:
        """
        Render simplified combined user profile and leaderboard.
        
        Args:
            user_info: User information dictionary
            user_id: Current user's ID
        """
        try:
            # Extract user data
            display_name, level, reviews_completed, score = self._extract_user_data(user_info)
            # Get user badges and rank
            user_badges = self.badge_manager.get_user_badges(user_id)[:3]  # Top 3 badges
            user_rank_info = self.badge_manager.get_user_rank(user_id)
            leaders = self.badge_manager.get_leaderboard_with_badges(8)
            
            # Render profile section
            self._render_profile_section(display_name, level, reviews_completed, score, 
                                       user_badges, user_rank_info)
            
            # Render leaderboard section
            if leaders:
                self._render_leaderboard_section(leaders, user_id)
                
        except Exception as e:
            logger.error(f"Error rendering sidebar: {str(e)}")
    
    def _extract_user_data(self, user_info: Dict[str, Any]) -> tuple:
        """Extract user data with language support."""
        current_lang = get_current_language()
        display_name = user_info.get(f"display_name_{current_lang}", 
                                   user_info.get("display_name", "User"))
        level = user_info.get(f"level_name_{current_lang}", 
                            user_info.get("level", "basic")).capitalize()
        reviews_completed = user_info.get("reviews_completed", 0)
        score = user_info.get("score", 0)
        return display_name, level, reviews_completed, score
    
    def _render_profile_section(self, display_name: str, level: str, reviews_completed: int, 
                          score: int, user_badges: List[Dict], user_rank_info: Dict) -> None:
        """Render profile section with properly formatted HTML."""
        
        # CSS (same as before)
        st.markdown("""
        <style>
        .profile-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 16px;
            padding: 0;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
            overflow: hidden;
        }
        .profile-header {
            padding: 24px 20px;
            text-align: center;
            color: white;
        }
        .profile-name {
            font-size: 1.4em;
            font-weight: 700;
            margin: 0 0 8px 0;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
            letter-spacing: 0.5px;
        }
        .profile-level {
            font-size: 0.95em;
            margin: 0 0 12px 0;
            opacity: 0.9;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .badge-container {
            display: flex;
            justify-content: center;
            gap: 8px;
            margin-top: 12px;
        }
        .badge-icon {
            font-size: 1.3em;
            padding: 6px 8px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .stats-container {
            background: rgba(255, 255, 255, 0.95);
            margin: 0 12px 12px 12px;
            border-radius: 12px;
            padding: 16px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
            margin-bottom: 16px;
        }
        .stat-item {
            text-align: center;
            padding: 12px;
            background: linear-gradient(135deg, #f8f9ff 0%, #e8ecff 100%);
            border-radius: 10px;
            border: 1px solid rgba(102, 126, 234, 0.1);
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 4px;
        }
        .stat-label {
            font-size: 0.8em;
            color: #6c757d;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .rank-display {
            color: white;
            padding: 10px 16px;
            border-radius: 8px;
            text-align: center;
            font-weight: 600;
            font-size: 0.9em;
            letter-spacing: 0.5px;
        }
        .rank-emoji {
            font-size: 1.2em;
            margin-right: 6px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Build badge icons safely
        badge_html = ""
        if user_badges:
            for badge in user_badges:
                badge_name = str(badge.get("name", "")).replace('"', '&quot;')
                badge_icon = str(badge.get("icon", "🏅"))
                badge_html += f'<span class="badge-icon" title="{badge_name}">{badge_icon}</span>'
        else:
            badge_html = '<span class="badge-icon" style="opacity: 0.5;">🏅</span>'
        
        # Build profile HTML in sections
        st.markdown(f"""
        <div class="profile-card">
            <div class="profile-header">
                <div class="profile-name">{display_name}</div>
                <div class="profile-level">{level}</div>
                <div class="badge-container">
                    {badge_html}
                </div>
            </div>
            <div class="stats-container">
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-value">{reviews_completed}</div>
                        <div class="stat-label">{t("review_times")}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value">{score}</div>
                        <div class="stat-label">{t("score")}</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Render rank separately to avoid HTML issues
        self._render_rank_section(user_rank_info)

    def _render_rank_section(self, user_rank_info: Dict) -> None:
        """Render rank section separately to avoid HTML formatting issues."""
        rank = user_rank_info.get("rank", 0)
        total = user_rank_info.get("total_users", 0)
        
        if rank == 0:
            return
        
        # Determine rank styling
        if rank == 1:
            emoji = "🥇"
            color = "#ffd700"
        elif rank == 2:
            emoji = "🥈"
            color = "#c0c0c0"
        elif rank == 3:
            emoji = "🥉"
            color = "#cd7f32"
        else:
            emoji = "🏆"
            color = "#28a745"
        
        # Use Streamlit info component instead of custom HTML
        st.info(f"{emoji} #{rank} {t('of')} {total} {t('users')}")

    def _render_leaderboard_section(self, leaders: List[Dict], user_id: str) -> None:
        """Render enhanced leaderboard section with corrected HTML structure."""
        
        st.markdown("""
        <style>
        .leaderboard-container {
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            margin-top: 20px;
        }
        .leaderboard-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 16px;
            font-weight: 600;
            font-size: 0.95em;
            text-align: center;
            letter-spacing: 0.5px;
        }
        .leaderboard-item {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            border-bottom: 1px solid #f1f3f4;
            transition: all 0.2s ease;
            position: relative;
        }
        .leaderboard-item:hover {
            background-color: #f8f9fa;
        }
        .leaderboard-item:last-child {
            border-bottom: none;
        }
        .leaderboard-item.current-user {
            background: linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(76, 175, 80, 0.05) 100%);
            border-left: 4px solid #4CAF50;
        }
        .leaderboard-item.current-user::before {
            content: '';
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            width: 8px;
            height: 8px;
            background: #4CAF50;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .rank-position {
            width: 32px;
            text-align: center;
            font-weight: bold;
            font-size: 1.1em;
        }
        .user-info {
            flex: 1;
            margin-left: 12px;
        }
        .user-name {
            font-weight: 600;
            color: #2c3e50;
            font-size: 0.9em;
            margin-bottom: 2px;
        }
        .user-badges {
            display: inline-block;
            margin-left: 6px;
        }
        .user-badges span {
            font-size: 0.8em;
            margin-right: 2px;
        }
        .user-points {
            font-weight: 700;
            color: #667eea;
            font-size: 0.9em;
            text-align: right;
            min-width: 50px;
        }
        .current-user-indicator {
            color: #4CAF50;
            font-size: 0.75em;
            font-weight: 600;
            margin-left: 4px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Build leaderboard HTML with correct structure
        items_html = ""
        for leader in leaders[:5]:
            rank = leader.get("rank", 0)
            name = leader.get("display_name", t("unknown"))
            points = leader.get("total_points", 0)
            badges = leader.get("top_badges", [])[:2]
            is_current = leader.get("uid") == user_id
            
            # Format elements
            rank_emoji = self._get_rank_emoji(rank)
            badge_icons = self._get_compact_badge_icons(badges)
            current_class = "current-user" if is_current else ""
            current_indicator = f'<span class="current-user-indicator">({t("you")})</span>' if is_current else ""
            
            # Truncate name if too long
            display_name = name[:12] + "..." if len(name) > 12 else name
            
            items_html += f"""
            <div class="leaderboard-item {current_class}">
                <div class="rank-position">{rank_emoji}</div>
                <div class="user-info">
                    <div class="user-name">
                        {display_name}{current_indicator}
                        <span class="user-badges">{badge_icons}</span>
                    </div>
                </div>
                <div class="user-points">{points:,}</div>
            </div>"""
        
        # Complete leaderboard HTML
        st.markdown(f"""
        <div class="leaderboard-container">
            <div class="leaderboard-header">
                🏆 {t("leaderboard")} - {t("points")}
            </div>
            {items_html}
        </div>
        """, unsafe_allow_html=True)
    
    def _get_rank_emoji(self, rank: int) -> str:
        """Get emoji for rank."""
        return "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"{rank}."
    
  