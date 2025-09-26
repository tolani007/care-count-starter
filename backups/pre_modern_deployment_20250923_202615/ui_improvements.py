"""
Care Count UI/UX Improvements Module
Industry-standard UI components and styling
"""

import streamlit as st
from typing import Dict, Any, Optional
import base64
from pathlib import Path

class ModernUIComponents:
    """Modern UI components for Care Count app"""
    
    @staticmethod
    def get_modern_css() -> str:
        """Return modern, industry-standard CSS"""
        return """
        <style>
        /* Modern Design System */
        :root {
            /* Color Palette - Laurier Theme Enhanced */
            --primary-purple: #6d28d9;
            --primary-gold: #fde047;
            --primary-dark: #0b1420;
            --secondary-dark: #0f1a2a;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-orange: #f59e0b;
            
            /* Neutral Colors */
            --gray-50: #f9fafb;
            --gray-100: #f3f4f6;
            --gray-200: #e5e7eb;
            --gray-300: #d1d5db;
            --gray-400: #9ca3af;
            --gray-500: #6b7280;
            --gray-600: #4b5563;
            --gray-700: #374151;
            --gray-800: #1f2937;
            --gray-900: #111827;
            
            /* Typography */
            --font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            --font-size-xs: 0.75rem;
            --font-size-sm: 0.875rem;
            --font-size-base: 1rem;
            --font-size-lg: 1.125rem;
            --font-size-xl: 1.25rem;
            --font-size-2xl: 1.5rem;
            --font-size-3xl: 1.875rem;
            
            /* Spacing */
            --space-1: 0.25rem;
            --space-2: 0.5rem;
            --space-3: 0.75rem;
            --space-4: 1rem;
            --space-5: 1.25rem;
            --space-6: 1.5rem;
            --space-8: 2rem;
            --space-10: 2.5rem;
            --space-12: 3rem;
            
            /* Border Radius */
            --radius-sm: 0.375rem;
            --radius-md: 0.5rem;
            --radius-lg: 0.75rem;
            --radius-xl: 1rem;
            --radius-2xl: 1.5rem;
            
            /* Shadows */
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
            --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
            --shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
        }
        
        /* Global Styles */
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: var(--font-family);
            background: var(--primary-dark);
            color: var(--gray-100);
            line-height: 1.6;
        }
        
        /* Streamlit Overrides */
        .main .block-container {
            padding: var(--space-6) var(--space-4);
            max-width: 1200px;
        }
        
        .stApp {
            background: var(--primary-dark);
        }
        
        /* Typography */
        h1, h2, h3, h4, h5, h6 {
            font-weight: 700;
            letter-spacing: -0.025em;
            color: var(--gray-100);
        }
        
        h1 {
            font-size: var(--font-size-3xl);
            margin-bottom: var(--space-6);
        }
        
        h2 {
            font-size: var(--font-size-2xl);
            margin-bottom: var(--space-4);
        }
        
        h3 {
            font-size: var(--font-size-xl);
            margin-bottom: var(--space-3);
        }
        
        /* Modern Cards */
        .modern-card {
            background: var(--secondary-dark);
            border: 1px solid var(--gray-700);
            border-radius: var(--radius-xl);
            padding: var(--space-6);
            margin-bottom: var(--space-4);
            box-shadow: var(--shadow-lg);
            transition: all 0.2s ease;
        }
        
        .modern-card:hover {
            border-color: var(--primary-purple);
            box-shadow: var(--shadow-xl);
        }
        
        /* Status Cards */
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: var(--space-4);
            margin-bottom: var(--space-6);
        }
        
        .status-card {
            background: var(--secondary-dark);
            border: 1px solid var(--gray-700);
            border-radius: var(--radius-lg);
            padding: var(--space-4);
            text-align: center;
            transition: all 0.2s ease;
        }
        
        .status-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg);
        }
        
        .status-card h4 {
            margin: 0 0 var(--space-2) 0;
            font-size: var(--font-size-sm);
            color: var(--gray-400);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .status-card .value {
            font-size: var(--font-size-2xl);
            font-weight: 800;
            color: var(--primary-gold);
            margin: 0;
        }
        
        .status-card .subtitle {
            font-size: var(--font-size-xs);
            color: var(--gray-500);
            margin: var(--space-1) 0 0 0;
        }
        
        /* Modern Buttons */
        .modern-btn {
            background: var(--primary-purple);
            color: white;
            border: none;
            border-radius: var(--radius-md);
            padding: var(--space-3) var(--space-6);
            font-weight: 600;
            font-size: var(--font-size-sm);
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-sm);
        }
        
        .modern-btn:hover {
            background: #5b21b6;
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
        }
        
        .modern-btn:active {
            transform: translateY(0);
        }
        
        .modern-btn-secondary {
            background: var(--gray-700);
            color: var(--gray-100);
        }
        
        .modern-btn-secondary:hover {
            background: var(--gray-600);
        }
        
        .modern-btn-success {
            background: var(--accent-green);
        }
        
        .modern-btn-success:hover {
            background: #059669;
        }
        
        .modern-btn-danger {
            background: var(--accent-red);
        }
        
        .modern-btn-danger:hover {
            background: #dc2626;
        }
        
        /* Form Elements */
        .modern-input {
            background: var(--secondary-dark);
            border: 1px solid var(--gray-600);
            border-radius: var(--radius-md);
            padding: var(--space-3);
            color: var(--gray-100);
            font-size: var(--font-size-sm);
            transition: all 0.2s ease;
        }
        
        .modern-input:focus {
            outline: none;
            border-color: var(--primary-purple);
            box-shadow: 0 0 0 3px rgb(109 40 217 / 0.1);
        }
        
        /* Hero Section */
        .hero-section {
            background: linear-gradient(135deg, var(--primary-purple) 0%, var(--accent-blue) 100%);
            border-radius: var(--radius-2xl);
            padding: var(--space-8);
            margin-bottom: var(--space-8);
            text-align: center;
            color: white;
        }
        
        .hero-section h1 {
            color: white;
            margin-bottom: var(--space-4);
        }
        
        .hero-section p {
            font-size: var(--font-size-lg);
            opacity: 0.9;
            margin: 0;
        }
        
        /* Progress Indicators */
        .progress-bar {
            background: var(--gray-700);
            border-radius: var(--radius-lg);
            height: 8px;
            overflow: hidden;
            margin: var(--space-2) 0;
        }
        
        .progress-fill {
            background: linear-gradient(90deg, var(--primary-purple), var(--primary-gold));
            height: 100%;
            transition: width 0.3s ease;
        }
        
        /* Badges */
        .badge {
            display: inline-block;
            padding: var(--space-1) var(--space-2);
            border-radius: var(--radius-sm);
            font-size: var(--font-size-xs);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        
        .badge-success {
            background: var(--accent-green);
            color: white;
        }
        
        .badge-warning {
            background: var(--accent-orange);
            color: white;
        }
        
        .badge-danger {
            background: var(--accent-red);
            color: white;
        }
        
        .badge-info {
            background: var(--accent-blue);
            color: white;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .main .block-container {
                padding: var(--space-4) var(--space-2);
            }
            
            .status-grid {
                grid-template-columns: 1fr;
            }
            
            .hero-section {
                padding: var(--space-6);
            }
            
            h1 {
                font-size: var(--font-size-2xl);
            }
        }
        
        /* Loading States */
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid var(--gray-600);
            border-radius: 50%;
            border-top-color: var(--primary-purple);
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Animations */
        .fade-in {
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .slide-in {
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from { transform: translateX(-100%); }
            to { transform: translateX(0); }
        }
        
        /* Accessibility */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }
        
        /* Focus states for accessibility */
        button:focus,
        input:focus,
        select:focus,
        textarea:focus {
            outline: 2px solid var(--primary-purple);
            outline-offset: 2px;
        }
        </style>
        """
    
    @staticmethod
    def create_hero_section(title: str, subtitle: str, user_email: str = None) -> str:
        """Create a modern hero section"""
        if user_email:
            return f"""
            <div class="hero-section fade-in">
                <h1>💜💛 {title}</h1>
                <p>{subtitle}</p>
                <div style="margin-top: var(--space-4); padding: var(--space-4); background: rgba(255,255,255,0.1); border-radius: var(--radius-lg);">
                    <div style="font-size: var(--font-size-sm); opacity: 0.8;">Welcome,</div>
                    <div style="font-weight: 800; font-size: var(--font-size-lg); margin: var(--space-1) 0;">{user_email}</div>
                    <div style="font-size: var(--font-size-sm); opacity: 0.8;">Thank you for showing up for the community today. 💜💛</div>
                </div>
            </div>
            """
        else:
            return f"""
            <div class="hero-section fade-in">
                <h1>💜💛 {title}</h1>
                <p>{subtitle}</p>
            </div>
            """
    
    @staticmethod
    def create_status_cards(data: Dict[str, Any]) -> str:
        """Create modern status cards"""
        cards_html = '<div class="status-grid">'
        
        for key, value in data.items():
            if key == "shift_active":
                cards_html += f"""
                <div class="status-card slide-in">
                    <h4>Shift Active</h4>
                    <div class="value">{value}</div>
                    <div class="subtitle">since you signed in</div>
                </div>
                """
            elif key == "items_today":
                cards_html += f"""
                <div class="status-card slide-in">
                    <h4>Items Logged Today</h4>
                    <div class="value">{value}</div>
                    <div class="subtitle">items processed</div>
                </div>
                """
            elif key == "lifetime_hours":
                cards_html += f"""
                <div class="status-card slide-in">
                    <h4>Lifetime Hours</h4>
                    <div class="value">{value}</div>
                    <div class="subtitle">volunteer hours</div>
                </div>
                """
        
        cards_html += '</div>'
        return cards_html
    
    @staticmethod
    def create_modern_form_section(title: str, description: str = None) -> str:
        """Create a modern form section header"""
        desc_html = f'<p style="color: var(--gray-400); margin-bottom: var(--space-4);">{description}</p>' if description else ''
        return f"""
        <div class="modern-card fade-in">
            <h3>{title}</h3>
            {desc_html}
        """
    
    @staticmethod
    def create_progress_indicator(current: int, total: int, label: str) -> str:
        """Create a modern progress indicator"""
        percentage = (current / total * 100) if total > 0 else 0
        return f"""
        <div style="margin: var(--space-4) 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--space-2);">
                <span style="font-weight: 600; color: var(--gray-300);">{label}</span>
                <span style="font-weight: 700; color: var(--primary-gold);">{current}/{total}</span>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" style="width: {percentage}%;"></div>
            </div>
        </div>
        """
    
    @staticmethod
    def create_badge(text: str, variant: str = "info") -> str:
        """Create a modern badge"""
        return f'<span class="badge badge-{variant}">{text}</span>'
    
    @staticmethod
    def create_loading_spinner() -> str:
        """Create a loading spinner"""
        return '<div class="loading"></div>'

def apply_modern_ui():
    """Apply modern UI styling to the Streamlit app"""
    st.markdown(ModernUIComponents.get_modern_css(), unsafe_allow_html=True)

def create_modern_layout():
    """Create a modern layout structure"""
    return {
        "container_style": "max-width: 1200px; margin: 0 auto;",
        "sidebar_style": "background: var(--secondary-dark); border-right: 1px solid var(--gray-700);",
        "main_style": "background: var(--primary-dark); padding: var(--space-6);"
    }
