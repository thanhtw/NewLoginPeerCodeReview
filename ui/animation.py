"""
Animation utilities for the Java Peer Code Review Training System.
"""

import streamlit as st
import time

def level_up_animation(old_level: str, new_level: str) -> None:
    """
    Display a level-up animation when a user advances to a new level.
    
    Args:
        old_level: Previous user level
        new_level: New user level
    """
    # Create a container for the animation
    container = st.container()
    
    with container:
        # Initial state
        st.markdown(f"""
        <div style="position: relative; height: 200px; width: 100%; 
                    background: linear-gradient(135deg, rgba(0,0,150,0.1), rgba(0,150,0,0.1)); 
                    border-radius: 10px; overflow: hidden;">
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                        text-align: center; width: 100%;">
                <div style="font-size: 1.5rem; margin-bottom: 10px; color: #666;">Level Up!</div>
                <div style="font-size: 2.5rem; font-weight: bold; color: #333;">
                    {old_level.capitalize()} → {new_level.capitalize()}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Play sound effect (if sound is enabled in Streamlit)
    # We can't actually play sounds directly in Streamlit, but
    # we could use visual effects instead
    
    # Animate with fireworks effect
    for i in range(5):
        firework_left = (i * 20) % 80
        firework_top = 10 + (i * 15) % 40
        
        with container:
            st.markdown(f"""
            <div style="position: relative; height: 200px; width: 100%; 
                        background: linear-gradient(135deg, rgba(0,0,150,0.1), rgba(0,150,0,0.1)); 
                        border-radius: 10px; overflow: hidden;">
                <div style="position: absolute; top: {firework_top}%; left: {firework_left}%; 
                            animation: firework 0.5s ease-out;">
                    <div style="font-size: 2rem;">✨</div>
                </div>
                <div style="position: absolute; top: {firework_top + 40}%; left: {firework_left + 40}%; 
                            animation: firework 0.5s ease-out;">
                    <div style="font-size: 2rem;">🎉</div>
                </div>
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                            text-align: center; width: 100%;">
                    <div style="font-size: 1.5rem; margin-bottom: 10px; color: #666;">Level Up!</div>
                    <div style="font-size: 2.5rem; font-weight: bold; color: #333;">
                        {old_level.capitalize()} → {new_level.capitalize()}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Add small delay between animation frames
        time.sleep(0.3)
    
    # Final state
    with container:
        st.markdown(f"""
        <div style="position: relative; height: 200px; width: 100%; 
                    background: linear-gradient(135deg, rgba(0,100,0,0.1), rgba(0,150,100,0.1)); 
                    border-radius: 10px; overflow: hidden;">
            <div style="position: absolute; top: 10%; left: 10%; animation: firework 0.5s ease-out;">
                <div style="font-size: 2rem;">✨</div>
            </div>
            <div style="position: absolute; top: 15%; left: 80%; animation: firework 0.5s ease-out;">
                <div style="font-size: 2rem;">🎉</div>
            </div>
            <div style="position: absolute; top: 70%; left: 20%; animation: firework 0.5s ease-out;">
                <div style="font-size: 2rem;">🏆</div>
            </div>
            <div style="position: absolute; top: 65%; left: 75%; animation: firework 0.5s ease-out;">
                <div style="font-size: 2rem;">🌟</div>
            </div>
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                        text-align: center; width: 100%;">
                <div style="font-size: 1.5rem; margin-bottom: 10px; color: #666;">Congratulations!</div>
                <div style="font-size: 2.5rem; font-weight: bold; color: #333;">
                    You've reached {new_level.capitalize()} Level!
                </div>
                <div style="margin-top: 15px;">
                    <span style="padding: 5px 10px; background-color: rgba(0,150,0,0.2); 
                                border-radius: 5px; font-weight: bold;">
                        New badges and challenges unlocked!
                    </span>
                </div>
            </div>
            <style>
            </style>
        </div>
        """, unsafe_allow_html=True)
    
    # After animation, we could also show a message about new unlocked features
    st.success(f"You've been promoted to {new_level.capitalize()} level! New challenges and badges are now available.")