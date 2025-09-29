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
        /* Modern Design System - Laurier University Inspired */
        :root {
            /* Color Palette - Laurier University Theme */
            --primary-purple: #6b46c1;  /* Laurier purple - more vibrant */
            --primary-gold: #fbbf24;    /* Laurier gold - warmer tone */
            --primary-dark: #1e1b4b;    /* Deep purple background */
            --secondary-dark: #312e81;  /* Slightly lighter purple */
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
            background: var(--gray-900);
            color: var(--gray-100);
            line-height: 1.6;
        }
        
        /* Streamlit Overrides */
        .main .block-container {
            padding: var(--space-6) var(--space-4);
            max-width: 1200px;
            background: var(--gray-900);
        }
        
        .stApp {
            background: var(--gray-900);
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
        
        /* Modern Cards - Laurier Style */
        .modern-card {
            background: var(--gray-800);
            border: 1px solid var(--gray-700);
            border-radius: var(--radius-xl);
            padding: var(--space-6);
            margin-bottom: var(--space-4);
            box-shadow: var(--shadow-md);
            transition: all 0.2s ease;
            color: var(--gray-100);
        }
        
        .modern-card:hover {
            border-color: var(--primary-purple);
            box-shadow: var(--shadow-lg);
            transform: translateY(-2px);
        }
        
        .modern-card:hover h1,
        .modern-card:hover h2,
        .modern-card:hover h3,
        .modern-card:hover h4,
        .modern-card:hover h5,
        .modern-card:hover h6,
        .modern-card:hover p,
        .modern-card:hover span,
        .modern-card:hover div {
            color: var(--gray-100) !important;
        }
        
        /* Status Cards */
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: var(--space-4);
            margin-bottom: var(--space-6);
        }
        
        .status-card {
            background: var(--gray-800);
            border: 1px solid var(--gray-700);
            border-radius: var(--radius-lg);
            padding: var(--space-5);
            text-align: center;
            transition: all 0.2s ease;
            box-shadow: var(--shadow-sm);
        }
        
        .status-card:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
            border-color: var(--primary-purple);
        }
        
        .status-card:hover h4,
        .status-card:hover .value,
        .status-card:hover .subtitle {
            color: var(--gray-100) !important;
        }
        
        .status-card:hover .value {
            color: var(--primary-purple) !important;
        }
        
        .status-card h4 {
            margin: 0 0 var(--space-2) 0;
            font-size: var(--font-size-sm);
            color: var(--gray-300);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        
        .status-card .value {
            font-size: var(--font-size-2xl);
            font-weight: 800;
            color: var(--primary-purple);
            margin: 0;
        }
        
        .status-card .subtitle {
            font-size: var(--font-size-xs);
            color: var(--gray-400);
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
            position: relative;
        }
        
        .modern-btn:hover {
            background: #5b21b6;
            transform: translateY(-1px);
            box-shadow: var(--shadow-md);
            color: white !important;
        }
        
        .modern-btn:active {
            transform: translateY(0);
        }
        
        /* Tooltip styles */
        .tooltip {
            position: relative;
            display: inline-block;
        }
        
        .tooltip .tooltiptext {
            visibility: hidden;
            width: 200px;
            background-color: var(--gray-800);
            color: white;
            text-align: center;
            border-radius: var(--radius-md);
            padding: var(--space-2) var(--space-3);
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -100px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: var(--font-size-xs);
            box-shadow: var(--shadow-lg);
        }
        
        .tooltip .tooltiptext::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: var(--gray-800) transparent transparent transparent;
        }
        
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        
        /* Fix Streamlit error/warning message visibility */
        .stAlert {
            border: 1px solid var(--accent-red) !important;
            border-radius: var(--radius-md) !important;
            padding: var(--space-3) !important;
            margin: var(--space-2) 0 !important;
        }
        
        .stAlert[data-testid="error"] {
            background-color: #fef2f2 !important;
            border-color: #fca5a5 !important;
        }
        
        .stAlert[data-testid="error"] .stMarkdown {
            color: #dc2626 !important;
            font-weight: 600 !important;
        }
        
        .stAlert[data-testid="warning"] {
            background-color: #fffbeb !important;
            border-color: #fbbf24 !important;
        }
        
        .stAlert[data-testid="warning"] .stMarkdown {
            color: #d97706 !important;
            font-weight: 600 !important;
        }
        
        .stAlert[data-testid="success"] {
            background-color: #f0fdf4 !important;
            border-color: #86efac !important;
        }
        
        .stAlert[data-testid="success"] .stMarkdown {
            color: #16a34a !important;
            font-weight: 600 !important;
        }
        
        .stAlert[data-testid="info"] {
            background-color: #eff6ff !important;
            border-color: #93c5fd !important;
        }
        
        .stAlert[data-testid="info"] .stMarkdown {
            color: #2563eb !important;
            font-weight: 600 !important;
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
            background: var(--gray-800);
            border: 1px solid var(--gray-600);
            border-radius: var(--radius-md);
            padding: var(--space-3);
            color: var(--gray-100);
            font-size: var(--font-size-sm);
            transition: all 0.2s ease;
        }
        
        .modern-input::placeholder {
            color: var(--gray-400);
        }
        
        .modern-input:focus {
            outline: none;
            border-color: var(--primary-purple);
            box-shadow: 0 0 0 3px rgb(107 70 193 / 0.25);
        }
        
        /* Hero Section - Laurier Style */
        .hero-section {
            background: var(--primary-purple);
            border-radius: var(--radius-2xl);
            padding: var(--space-10);
            margin-bottom: var(--space-8);
            text-align: left;
            color: white;
            box-shadow: var(--shadow-xl);
            position: relative;
            overflow: hidden;
        }
        
        .hero-section::before {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 40%;
            height: 100%;
            background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%);
            border-radius: 0 var(--radius-2xl) var(--radius-2xl) 0;
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
        
        /* Streamlit Spinner Overrides */
        .stSpinner > div {
            background-color: var(--primary-purple) !important;
            border-color: var(--primary-purple) !important;
        }
        
        /* Prevent layout shifts during loading */
        .stSpinner {
            position: relative;
            z-index: 1000;
        }
        
        /* Loading state containers */
        .loading-container {
            position: relative;
            min-height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--gray-800);
            border-radius: var(--radius-md);
            border: 1px solid var(--gray-700);
            padding: var(--space-4);
        }
        
        /* Smooth transitions for form states */
        .modern-card {
            transition: all 0.3s ease;
        }
        
        .modern-card.loading {
            opacity: 0.7;
            pointer-events: none;
        }
        
        /* Prevent content jumping during state changes */
        .form-section {
            min-height: 200px;
        }
        
        /* Status messages */
        .status-message {
            padding: var(--space-3) var(--space-4);
            border-radius: var(--radius-md);
            margin: var(--space-2) 0;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: var(--space-2);
        }
        
        .status-info {
            background: var(--gray-800);
            border: 1px solid var(--gray-700);
            color: var(--gray-200);
        }
        
        .status-success {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid var(--accent-green);
            color: var(--accent-green);
        }
        
        .status-warning {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid var(--accent-orange);
            color: var(--accent-orange);
        }
        
        .status-error {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--accent-red);
            color: var(--accent-red);
        }
        
        .status-loading {
            background: rgba(107, 70, 193, 0.1);
            border: 1px solid var(--primary-purple);
            color: var(--primary-purple);
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

        /* Laurier Cares Bags Celebration Animation */
        .bags-overlay {
            position: fixed;
            inset: 0;
            pointer-events: none;
            z-index: 9999;
            overflow: hidden;
        }
        .bag {
            position: absolute;
            top: -120px;
            width: 80px;
            height: 100px;
            background: linear-gradient(180deg, #7C3AED, #5B21B6);
            border-radius: 8px 8px 12px 12px;
            box-shadow: var(--shadow-lg);
            border: 2px solid rgba(255,255,255,0.2);
            animation: bagDrop 2.8s ease-in forwards;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 11px;
            text-align: center;
            padding: 6px;
        }
        .bag:before {
            content: "";
            position: absolute;
            top: -14px;
            left: 22px;
            width: 36px;
            height: 22px;
            border: 3px solid rgba(255,255,255,0.7);
            border-bottom: none;
            border-radius: 18px 18px 0 0;
        }
        .bag .label {
            font-size: 10px;
            line-height: 1.1;
            letter-spacing: 0.3px;
        }
        @keyframes bagDrop {
            0% { transform: translateY(-140px) rotate(0deg); opacity: 0; }
            10% { opacity: 1; }
            80% { transform: translateY(100vh) rotate(10deg); }
            100% { transform: translateY(110vh) rotate(14deg); opacity: 0; }
        }
        .bags-overlay.fade-out { animation: overlayFade 0.4s ease forwards; }
        @keyframes overlayFade {
            to { opacity: 0; }
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
        """Create a Laurier-style hero section"""
        if user_email:
            return f"""
            <div class="hero-section fade-in">
                <div style="position: relative; z-index: 2;">
                    <h1 style="font-size: 2.5rem; margin-bottom: var(--space-4); color: white;">💜💛 {title}</h1>
                    <p style="font-size: 1.25rem; margin-bottom: var(--space-6); color: white; opacity: 0.9;">{subtitle}</p>
                    <div style="margin-top: var(--space-6); padding: var(--space-5); background: rgba(255,255,255,0.15); border-radius: var(--radius-lg); backdrop-filter: blur(10px);">
                        <div style="font-size: var(--font-size-sm); opacity: 0.8; color: white;">Welcome,</div>
                        <div style="font-weight: 800; font-size: var(--font-size-xl); margin: var(--space-2) 0; color: white;">{user_email}</div>
                        <div style="font-size: var(--font-size-sm); opacity: 0.8; color: white;">Thank you for showing up for the community today. 💜💛</div>
                    </div>
                </div>
            </div>
            """
        else:
            return f"""
            <div class="hero-section fade-in">
                <div style="position: relative; z-index: 2;">
                    <h1 style="font-size: 2.5rem; margin-bottom: var(--space-4); color: white;">💜💛 {title}</h1>
                    <p style="font-size: 1.25rem; color: white; opacity: 0.9;">{subtitle}</p>
                </div>
            </div>
            """
    
    @staticmethod
    def create_status_cards(data: Dict[str, Any]) -> str:
        """Create modern status cards (no markdown-indented lines)"""
        parts = ["<div class=\"status-grid\">"]
        for key, value in data.items():
            if key == "shift_active":
                parts.append(
                    "<div class=\"status-card slide-in\"><h4>Shift Active</h4>"
                    f"<div class=\"value\">{value}</div>"
                    "<div class=\"subtitle\">since you signed in</div></div>"
                )
            elif key == "items_today":
                parts.append(
                    "<div class=\"status-card slide-in\"><h4>Items Logged Today</h4>"
                    f"<div class=\"value\">{value}</div>"
                    "<div class=\"subtitle\">items processed</div></div>"
                )
            elif key == "lifetime_hours":
                parts.append(
                    "<div class=\"status-card slide-in\"><h4>Lifetime Hours</h4>"
                    f"<div class=\"value\">{value}</div>"
                    "<div class=\"subtitle\">volunteer hours</div></div>"
                )
        parts.append("</div>")
        return "".join(parts)
    
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
    
    @staticmethod
    def create_loading_container(message: str = "Loading...") -> str:
        """Create a loading container with message"""
        return f'''
        <div class="loading-container">
            <div class="loading"></div>
            <span style="margin-left: var(--space-3); color: var(--gray-300);">{message}</span>
        </div>
        '''
    
    @staticmethod
    def create_status_message(message: str, type: str = "info") -> str:
        """Create a status message with consistent styling"""
        icon_map = {
            "info": "ℹ️",
            "success": "✅", 
            "warning": "⚠️",
            "error": "❌",
            "loading": "🔄"
        }
        icon = icon_map.get(type, "ℹ️")
        return f'<div class="status-message status-{type}">{icon} {message}</div>'

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
