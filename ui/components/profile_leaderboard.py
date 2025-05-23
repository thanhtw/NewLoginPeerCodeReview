"""
Fixed Enhanced Leaderboard Rendering - Resolves HTML display issues
"""

import streamlit as st
import logging
from typing import Dict, Any, List
from auth.badge_manager import BadgeManager
from utils.language_utils import t, get_current_language

logger = logging.getLogger(__name__)

class ProfileLeaderboardSidebar:
    """Fixed enhanced combined profile and leaderboard sidebar component."""
    
    def __init__(self):
        self.badge_manager = BadgeManager()
    
    def render_combined_sidebar(self, user_info: Dict[str, Any], user_id: str) -> None:
        """
        Render enhanced combined user profile and leaderboard with fixed HTML rendering.
        """
        try:
            # Load CSS once
            self._load_fixed_sidebar_css()
            
            # Extract user data
            display_name, level, reviews_completed, score = self._extract_user_data(user_info)
            
            # Get user badges and rank
            user_badges = self.badge_manager.get_user_badges(user_id)[:4]
            user_rank_info = self.badge_manager.get_user_rank(user_id)
            leaders = self.badge_manager.get_leaderboard_with_badges(8)
            
            # Render profile section
            self._render_fixed_profile_section(display_name, level, reviews_completed, 
                                             score, user_badges, user_rank_info)
            
            # Render leaderboard section with proper error handling
            if leaders:
                self._render_fixed_leaderboard_section(leaders, user_id)
            else:
                st.info("No leaderboard data available")
                
        except Exception as e:
            logger.error(f"Error rendering enhanced sidebar: {str(e)}")
            # Show simple fallback
            self._render_simple_fallback(user_info)
    
    def _load_fixed_sidebar_css(self):
        """Load fixed CSS styles that work properly with Streamlit."""
        css_content = """
        <style>
        /* Streamlit sidebar specific fixes */
        .stSidebar .sidebar-container {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            color: #2c3e50;
            width: 100%;
        }
        
        /* Enhanced Profile Card - Fixed */
        .enhanced-profile-card {
            background: linear-gradient(145deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
            border-radius: 20px;
            padding: 0;
            margin-bottom: 20px;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.25);
            overflow: hidden;
            position: relative;
        }
        
        .profile-header-enhanced {
            padding: 24px 16px 16px;
            text-align: center;
            color: white;
            position: relative;
        }
        
        .profile-avatar {
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: rgba(255,255,255,0.2);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 12px;
            font-size: 1.8rem;
            font-weight: bold;
            border: 2px solid rgba(255,255,255,0.3);
        }
        
        .profile-name-enhanced {
            font-size: 1.3em;
            font-weight: 700;
            margin-bottom: 6px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        .profile-level-enhanced {
            font-size: 0.85em;
            opacity: 0.9;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 4px 12px;
            background: rgba(255,255,255,0.15);
            border-radius: 15px;
            display: inline-block;
            margin-bottom: 12px;
        }
        
        .badge-showcase-fixed {
            display: flex;
            justify-content: center;
            gap: 6px;
            flex-wrap: wrap;
        }
        
        .badge-icon-fixed {
            font-size: 1.2em;
            padding: 6px 8px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 8px;
            border: 1px solid rgba(255, 255, 255, 0.25);
            transition: transform 0.2s ease;
        }
        
        .badge-icon-fixed:hover {
            transform: scale(1.1);
        }
        
        .stats-grid-enhanced {
            background: rgba(255, 255, 255, 0.95);
            margin: 0 12px 12px;
            border-radius: 12px;
            padding: 16px;
        }
        
        .stats-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        
        .stat-item-enhanced {
            text-align: center;
            padding: 12px 8px;
            background: linear-gradient(145deg, #f8f9ff 0%, #e8ecff 100%);
            border-radius: 8px;
            border: 1px solid rgba(102, 126, 234, 0.1);
            position: relative;
        }
        
        .stat-item-enhanced::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }
        
        .stat-value-enhanced {
            font-size: 1.6em;
            font-weight: 800;
            color: #667eea;
            margin-bottom: 4px;
            line-height: 1;
        }
        
        .stat-label-enhanced {
            font-size: 0.7em;
            color: #6c757d;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        /* Rank Display - Fixed */
        .rank-display-fixed {
            background: linear-gradient(145deg, #28a745, #20c997);
            color: white;
            padding: 10px 14px;
            border-radius: 10px;
            text-align: center;
            font-weight: 700;
            font-size: 0.85em;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }
        
        /* Leaderboard Container - Fixed */
        .leaderboard-fixed {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            margin-bottom: 16px;
        }
        
        .leaderboard-header-fixed {
            background: linear-gradient(145deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 14px 16px;
            font-weight: 700;
            font-size: 1em;
            text-align: center;
        }
        
        .leaderboard-item-fixed {
            display: flex;
            align-items: center;
            padding: 2px 4px;
            border-bottom: 1px solid #f8f9fa;
            transition: background-color 0.2s ease;
        }
        
        .leaderboard-item-fixed:hover {
            background-color: #f8f9ff;
        }
        
        .leaderboard-item-fixed:last-child {
            border-bottom: none;
        }
        
        .leaderboard-item-fixed.current-user {
            background: linear-gradient(145deg, rgba(40, 167, 69, 0.08), rgba(32, 201, 151, 0.04));
            border-left: 3px solid #28a745;
            font-weight: 600;
        }
        
        .rank-pos-fixed {
            width: 35px;
            text-align: center;
            font-weight: 800;
            font-size: 1.1em;
            margin-right: 12px;
        }
        
        .rank-1 { color: #ffd700; }
        .rank-2 { color: #c0c0c0; }
        .rank-3 { color: #cd7f32; }
        
        .user-info-fixed {
            flex: 1;
            min-width: 0;
        }
        
        .user-name-fixed {
            font-weight: 600;
            color: #2c3e50;
            font-size: 0.9em;
            margin-bottom: 2px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .user-level-tag-fixed {
            font-size: 0.65em;
            padding: 1px 1px;
            background: linear-gradient(145deg, #667eea, #764ba2);
            color: white;
            border-radius: 8px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .user-badges-fixed {
            font-size: 0.8em;
            margin-top: 2px;
        }
        
        .user-points-fixed {
            font-weight: 700;
            color: #667eea;
            font-size: 1em;
            text-align: right;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }
        
        .points-num {
            font-size: 1.2em;
            line-height: 1;
        }
        
        .points-lbl {
            font-size: 0.65em;
            color: #95a5a6;
            font-weight: 500;
            text-transform: uppercase;
        }
        
        .current-user-tag {
            color: #28a745;
            font-size: 0.75em;
            font-weight: 600;
            margin-left: 4px;
            padding: 1px 4px;
            background: rgba(40, 167, 69, 0.1);
            border-radius: 4px;
        }
        
        /* Responsive fixes */
        @media (max-width: 768px) {
            .stats-row {
                grid-template-columns: 1fr;
                gap: 8px;
            }
            
            .leaderboard-item-fixed {
                padding: 10px 12px;
            }
        }
        </style>
        """
        
        # Use st.markdown with unsafe_allow_html=True
        st.markdown(css_content, unsafe_allow_html=True)
    
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
    
    def _render_fixed_profile_section(self, display_name: str, level: str, 
                                    reviews_completed: int, score: int, 
                                    user_badges: List[Dict], user_rank_info: Dict) -> None:
        """Render profile section with fixed HTML structure."""
        
        # Get user avatar (first letter)
        avatar_letter = display_name[0].upper() if display_name else "U"
        
        # Build badge HTML safely
        badge_html = ""
        if user_badges:
            for badge in user_badges[:4]:  # Limit to 4 badges
                icon = badge.get("icon", "🏅")
                badge_html += f'<span class="badge-icon-fixed">{icon}</span>'
        else:
            badge_html = '<span class="badge-icon-fixed">🏅</span>'
        
        # Profile HTML - using smaller, safer structure
        profile_html = f'''
        <div class="sidebar-container">
            <div class="enhanced-profile-card">
                <div class="profile-header-enhanced">
                    <div class="profile-avatar">{avatar_letter}</div>
                    <div class="profile-name-enhanced">{display_name}</div>
                    <div class="profile-level-enhanced">{level}</div>
                    <div class="badge-showcase-fixed">
                        {badge_html}
                    </div>
                </div>
                <div class="stats-grid-enhanced">
                    <div class="stats-row">
                        <div class="stat-item-enhanced">
                            <div class="stat-value-enhanced">{reviews_completed}</div>
                            <div class="stat-label-enhanced">{t("review_times")}</div>
                        </div>
                        <div class="stat-item-enhanced">
                            <div class="stat-value-enhanced">{score:,}</div>
                            <div class="stat-label-enhanced">{t("score")}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
        
        # Render profile with error handling
        try:
            st.markdown(profile_html, unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Error rendering profile HTML: {str(e)}")
            # Fallback to simple display
            st.markdown(f"**{display_name}** ({level})")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Reviews", reviews_completed)
            with col2:
                st.metric("Score", f"{score:,}")
        
        # Render rank section separately
        self._render_rank_section(user_rank_info)
    
    def _render_rank_section(self, user_rank_info: Dict) -> None:
        """Render rank section with fallback."""
        rank = user_rank_info.get("rank", 0)
        total = user_rank_info.get("total_users", 0)
        
        if rank == 0:
            return
        
        # Determine emoji and styling
        if rank == 1:
            emoji = "🥇"
        elif rank == 2:
            emoji = "🥈"
        elif rank == 3:
            emoji = "🥉"
        else:
            emoji = "🏆"
        
        rank_html = f'''
        <div class="rank-display-fixed">
            <span>{emoji}</span>
            <span>#{rank} {t('of')} {total:,} {t('users')}</span>
        </div>
        '''
        
        try:
            st.markdown(rank_html, unsafe_allow_html=True)
        except Exception as e:
            logger.error(f"Error rendering rank: {str(e)}")
            # Fallback
            st.info(f"{emoji} Rank: #{rank} of {total:,}")
    
    def _render_fixed_leaderboard_section(self, leaders: List[Dict], user_id: str) -> None:
        """
        Render leaderboard with beautiful CSS styling that actually works.
        This version carefully structures the HTML to avoid rendering issues.
        """
        
        try:
            # First, ensure CSS is loaded
            self._ensure_leaderboard_css()
            
            # Build the leaderboard HTML in smaller, safer chunks
            header_html = '''
            <div class="leaderboard-container-enhanced">
                <div class="leaderboard-header-enhanced">
                    🏆 Top Performers
                </div>
                <div class="leaderboard-list">
            '''
            
            # Render header first
            st.markdown(header_html, unsafe_allow_html=True)
            
            # Build items HTML safely
            items_html = ""
            for i, leader in enumerate(leaders[:6]):  # Show top 6
                rank = leader.get("rank", i + 1)
                name = leader.get("display_name", "Unknown")[:10]  # Truncate long names
                level = leader.get("level", "basic").capitalize()
                points = leader.get("total_points", 0)
                badges = leader.get("top_badges", [])[:3]
                is_current = leader.get("uid") == user_id
                
                # Get rank display and styling
                if rank == 1:
                    rank_display = "🥇"
                    rank_class = "rank-1"
                elif rank == 2:
                    rank_display = "🥈"
                    rank_class = "rank-2"
                elif rank == 3:
                    rank_display = "🥉"
                    rank_class = "rank-3"
                else:
                    rank_display = str(rank)
                    rank_class = ""
                
                # Get badge icons
                badge_icons = "".join([badge.get("icon", "🏅") for badge in badges])
                
                # Current user styling
                current_class = "current-user-enhanced" if is_current else ""
                current_indicator = '<span class="current-user-indicator-enhanced">(You)</span>' if is_current else ""
                
                # Build individual item HTML
                item_html = f'''
                <div class="leaderboard-item-enhanced {current_class}">
                    <div class="rank-position-enhanced {rank_class}">{rank_display}</div>
                    <div class="user-info-enhanced">
                        <div class="user-name-enhanced">
                            {name}
                            <span class="user-level-tag">{level}</span>
                            {current_indicator}
                        </div>
                        <div class="user-badges-enhanced">{badge_icons}</div>
                    </div>
                    <div class="user-points-enhanced">
                        <div class="points-number">{points:,}</div>
                        <div class="points-label">points</div>
                    </div>
                </div>
                '''
                items_html += item_html
            
            # Render items
            st.markdown(items_html, unsafe_allow_html=True)
            
            # Close container and add button
            footer_html = '''
                </div>
                <button class="view-full-btn" onclick="alert('Feature coming soon!')">
                    📊 View Full Leaderboard
                </button>
            </div>
            '''
            
            st.markdown(footer_html, unsafe_allow_html=True)
            
        except Exception as e:
            logger.error(f"Error rendering styled leaderboard: {str(e)}")
            # Fallback to simple version
            self._render_simple_leaderboard_fallback(leaders[:5], user_id)
    
    def _render_leaderboard_items_safe(self, leaders: List[Dict], user_id: str) -> None:
        """Render leaderboard items using safe Streamlit components."""
        
        # Create container for leaderboard
        with st.container():
            st.markdown("🏆 **Top Performers**")
            
            for i, leader in enumerate(leaders):
                rank = leader.get("rank", i + 1)
                name = leader.get("display_name", "Unknown")
                level = leader.get("level", "basic").capitalize()
                points = leader.get("total_points", 0)
                badges = leader.get("top_badges", [])[:3]
                is_current = leader.get("uid") == user_id
                
                # Get rank emoji
                if rank == 1:
                    rank_display = "🥇"
                elif rank == 2:
                    rank_display = "🥈"
                elif rank == 3:
                    rank_display = "🥉"
                else:
                    rank_display = f"#{rank}"
                
                # Get badges
                badge_str = "".join([badge.get("icon", "🏅") for badge in badges])
                
                # Current user indicator
                current_indicator = " 👤 (You)" if is_current else ""
                
                # Use columns for layout
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col1:
                    st.markdown(f"**{rank_display}**")
                
                with col2:
                    if is_current:
                        st.markdown(f"**{name}** {level}{current_indicator}")
                    else:
                        st.markdown(f"{name} {level}")
                    if badge_str:
                        st.markdown(f"<small>{badge_str}</small>", unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"**{points:,}**")
                
                # Add separator except for last item
                if i < len(leaders) - 1:
                    st.markdown("---")
    
    def _render_simple_leaderboard(self, leaders: List[Dict], user_id: str) -> None:
        """Simple fallback leaderboard using basic Streamlit components."""
        st.markdown("### 🏆 Leaderboard")
        
        for i, leader in enumerate(leaders):
            name = leader.get("display_name", "Unknown")
            points = leader.get("total_points", 0)
            is_current = leader.get("uid") == user_id
            
            rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
            current_text = " (You)" if is_current else ""
            
            st.markdown(f"{rank_emoji} **{name}**{current_text} - {points:,} pts")
    
    def _render_simple_fallback(self, user_info: Dict[str, Any]) -> None:
        """Simple fallback when everything else fails."""
        current_lang = get_current_language()
        display_name = user_info.get(f"display_name_{current_lang}", 
                                   user_info.get("display_name", "User"))
        score = user_info.get("score", 0)
        reviews = user_info.get("reviews_completed", 0)
        
        st.markdown(f"### 👤 {display_name}")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Reviews", reviews)
        with col2:
            st.metric("Score", f"{score:,}")

    def _show_expanded_leaderboard(self, leaders: List[Dict], user_id: str) -> None:
        """Show expanded leaderboard in a modal/expander."""
        with st.expander("🏆 Full Leaderboard", expanded=True):
            for i, leader in enumerate(leaders):
                name = leader.get("display_name", "Unknown")
                points = leader.get("total_points", 0)
                level = leader.get("level", "basic").capitalize()
                is_current = leader.get("uid") == user_id
                
                rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
                current_text = " 👤" if is_current else ""
                
                st.markdown(f"{rank_emoji} **{name}** *{level}*{current_text} - {points:,} pts")

    def _render_simple_leaderboard_fallback(self, leaders: List[Dict], user_id: str) -> None:
        """Simple fallback leaderboard."""
        st.markdown("### 🏆 Leaderboard")
        
        for i, leader in enumerate(leaders):
            name = leader.get("display_name", "Unknown")
            points = leader.get("total_points", 0)
            is_current = leader.get("uid") == user_id
            
            rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
            current_text = " (You)" if is_current else ""
            
            st.markdown(f"{rank_emoji} **{name}**{current_text} - {points:,} pts")

    def _ensure_leaderboard_css(self):
        """Ensure the beautiful leaderboard CSS is loaded."""
        
        # Check if CSS is already loaded to avoid duplicates
        if not hasattr(st.session_state, 'leaderboard_css_loaded'):
            
            leaderboard_css = """
            <style>
            /* Enhanced Leaderboard Styling */
            .leaderboard-container-enhanced {
                background: white;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 8px 32px rgba(0,0,0,0.08);
                margin-top: 24px;
                border: 1px solid rgba(0,0,0,0.05);
                animation: fadeIn 0.6s ease-in;
            }
            
            .leaderboard-header-enhanced {
                background: linear-gradient(145deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 18px 20px;
                font-weight: 700;
                font-size: 1.1em;
                text-align: center;
                letter-spacing: 0.5px;
                position: relative;
            }
            
            .leaderboard-header-enhanced::after {
                content: '';
                position: absolute;
                bottom: -10px;
                left: 50%;
                transform: translateX(-50%);
                width: 0;
                height: 0;
                border-left: 10px solid transparent;
                border-right: 10px solid transparent;
                border-top: 10px solid #764ba2;
            }
            
            .leaderboard-list {
                max-height: 400px;
                overflow-y: auto;
                scrollbar-width: thin;
                scrollbar-color: #667eea #f1f3f4;
            }
            
            .leaderboard-list::-webkit-scrollbar {
                width: 6px;
            }
            
            .leaderboard-list::-webkit-scrollbar-track {
                background: #f1f3f4;
            }
            
            .leaderboard-list::-webkit-scrollbar-thumb {
                background: #667eea;
                border-radius: 3px;
            }
            
            .leaderboard-item-enhanced {
                display: flex;
                align-items: center;
                padding: 10px;
                border-bottom: 1px solid #f8f9fa;
                transition: all 0.3s ease;
                position: relative;
                background: white;
            }
            
            .leaderboard-item-enhanced:hover {
                background: linear-gradient(145deg, #f8f9ff 0%, #f0f2ff 100%);
                transform: translateX(4px);
            }
            
            .leaderboard-item-enhanced:last-child {
                border-bottom: none;
            }
            
            .leaderboard-item-enhanced.current-user-enhanced {
                background: linear-gradient(145deg, rgba(40, 167, 69, 0.08) 0%, rgba(32, 201, 151, 0.05) 100%);
                border-left: 4px solid #28a745;
                font-weight: 600;
            }
            
            .leaderboard-item-enhanced.current-user-enhanced::after {
                position: absolute;
                right: 16px;
                top: 50%;
                transform: translateY(-50%);
                font-size: 1.2em;
                opacity: 0.7;
            }
            
            .rank-position-enhanced {
                width: 40px;
                text-align: center;
                font-weight: 800;
                font-size: 1.2em;
                margin-right: 16px;
            }
            
            .rank-1 { color: #ffd700; text-shadow: 0 0 10px rgba(255, 215, 0, 0.5); }
            .rank-2 { color: #c0c0c0; text-shadow: 0 0 10px rgba(192, 192, 192, 0.5); }
            .rank-3 { color: #cd7f32; text-shadow: 0 0 10px rgba(205, 127, 50, 0.5); }
            
            .user-info-enhanced {
                flex: 1;
                min-width: 0;
            }
            
            .user-name-enhanced {
                font-weight: 700;
                color: #2c3e50;
                font-size: 0.95em;
                margin-bottom: 4px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .user-level-tag {
                font-size: 0.7em;
                padding: 2px 8px;
                background: linear-gradient(145deg, #667eea, #764ba2);
                color: white;
                border-radius: 12px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .user-badges-enhanced {
                display: flex;
                gap: 3px;
                margin-top: 4px;
            }
            
            .user-badges-enhanced span {
                font-size: 0.9em;
                filter: drop-shadow(0 1px 3px rgba(0,0,0,0.2));
            }
            
            .user-points-enhanced {
                font-weight: 800;
                color: #667eea;
                font-size: 1.1em;
                text-align: right;
                min-width: 60px;
                display: flex;
                flex-direction: column;
                align-items: flex-end;
            }
            
            .points-number {
                font-size: 0.9em;
                line-height: 1;
            }
            
            .points-label {
                font-size: 0.7em;
                color: #95a5a6;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-top: 2px;
            }
            
            .current-user-indicator-enhanced {
                color: #28a745;
                font-size: 0.8em;
                font-weight: 700;
                margin-left: 6px;
                padding: 2px 6px;
                background: rgba(40, 167, 69, 0.1);
                border-radius: 8px;
            }
            
            .view-full-btn {
                background: linear-gradient(145deg, #667eea, #764ba2);
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 0 0 20px 20px;
                font-weight: 600;
                font-size: 0.9em;
                cursor: pointer;
                transition: all 0.3s ease;
                width: 100%;
                letter-spacing: 0.5px;
            }
            
            .view-full-btn:hover {
                background: linear-gradient(145deg, #764ba2, #667eea);
                transform: translateY(-1px);
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            
            /* Responsive Design */
            @media (max-width: 768px) {
                .leaderboard-item-enhanced {
                    padding: 10px;
                    flex-wrap: wrap;
                }
                
                .rank-position-enhanced {
                    width: 20px;
                    font-size: 1em;
                }
                
                .user-name-enhanced {
                    font-size: 0.85em;
                }
                
                .user-level-tag {
                    font-size: 0.65em;
                    padding: 1px 6px;
                }
                
                .user-points-enhanced {
                    font-size: 1em;
                }
                
                .points-number {
                    font-size: 1.1em;
                }
            }
            </style>
            """
            
            st.markdown(leaderboard_css, unsafe_allow_html=True)
            st.session_state.leaderboard_css_loaded = True

    def _render_simple_leaderboard_fallback(self, leaders: List[Dict], user_id: str) -> None:
        """Simple fallback leaderboard with basic styling."""
        st.markdown("### 🏆 Top Performers")
        
        for i, leader in enumerate(leaders):
            name = leader.get("display_name", "Unknown")
            points = leader.get("total_problems", 0)
            level = leader.get("level", "basic").capitalize()
            is_current = leader.get("uid") == user_id
            
            rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else f"#{i+1}"
            current_text = " 👤" if is_current else ""
            
            # Use container with some basic styling
            with st.container():
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    st.markdown(rank_emoji)
                with col2:
                    st.markdown(f"**{name}** *{level}*{current_text}")
                with col3:
                    st.markdown(f"**{points:,}**")