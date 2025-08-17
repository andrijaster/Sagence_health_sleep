"""
Evaluation framework for analyzing saved sleep consultation conversations.
Provides detailed analysis and metrics for conversation quality assessment.
"""

import os
import sys
import json
import sqlite3
import argparse
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime

class ConversationEvaluator:
    """Evaluates and analyzes saved sleep consultation conversations."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found: {db_path}")
    
    def load_conversations(self) -> pd.DataFrame:
        """Load all conversations from database."""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT conversation_id, patient_name, patient_profile, start_time, end_time,
                   total_messages, doctor_summary, patient_summary, urgency_level,
                   epworth_score, high_risk_flags, completion_status, notes
            FROM conversations
            ORDER BY start_time DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Parse JSON fields
        df['patient_profile'] = df['patient_profile'].apply(json.loads)
        df['high_risk_flags'] = df['high_risk_flags'].apply(json.loads)
        
        return df
    
    def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a specific conversation."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT sender, message_content, timestamp, message_order
            FROM messages 
            WHERE conversation_id = ?
            ORDER BY message_order
        ''', (conversation_id,))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                'sender': row[0],
                'content': row[1],
                'timestamp': row[2],
                'order': row[3]
            })
        
        conn.close()
        return messages
    
    def analyze_conversation_quality(self, conversation_id: str) -> Dict[str, Any]:
        """Analyze the quality of a specific conversation."""
        messages = self.get_conversation_messages(conversation_id)
        
        if not messages:
            return {"error": "No messages found"}
        
        # Basic metrics
        total_messages = len(messages)
        doctor_messages = [m for m in messages if m['sender'] == 'doctor']
        patient_messages = [m for m in messages if m['sender'] == 'patient']
        
        # Check for key components
        analysis = {
            "conversation_id": conversation_id,
            "total_messages": total_messages,
            "doctor_messages": len(doctor_messages),
            "patient_messages": len(patient_messages),
            "conversation_balance": len(patient_messages) / len(doctor_messages) if doctor_messages else 0,
        }
        
        # Check for mandatory questionnaires
        doctor_text = " ".join([m['content'].lower() for m in doctor_messages])
        
        # Epworth Sleepiness Scale detection
        epworth_indicators = [
            "sitting and reading", "watching tv", "inactive in public", 
            "passenger in car", "lying down to rest", "sitting and talking",
            "after lunch", "stopped in traffic", "epworth", "doze off", "sleepiness scale"
        ]
        epworth_mentions = sum(1 for indicator in epworth_indicators if indicator in doctor_text)
        analysis["epworth_coverage"] = epworth_mentions >= 3  # At least 3 indicators
        
        # PSQI detection
        psqi_indicators = [
            "sleep quality", "fall asleep", "hours of sleep", "bedtime", 
            "wake time", "sleep medication", "trouble staying awake", "psqi"
        ]
        psqi_mentions = sum(1 for indicator in psqi_indicators if indicator in doctor_text)
        analysis["psqi_coverage"] = psqi_mentions >= 3
        
        # High-risk screening detection
        risk_indicators = [
            "driving", "fall asleep while", "occupation", "work", "safety",
            "muscle weakness", "cataplexy", "violent movements", "sleepwalking",
            "mental health", "mood", "depression", "anxiety"
        ]
        risk_mentions = sum(1 for indicator in risk_indicators if indicator in doctor_text)
        analysis["risk_screening"] = risk_mentions >= 4
        
        # Check for one-question-at-a-time pattern
        multi_question_violations = 0
        for msg in doctor_messages:
            question_count = msg['content'].count('?')
            if question_count > 1:
                multi_question_violations += 1
        
        analysis["single_question_adherence"] = multi_question_violations == 0
        analysis["multi_question_violations"] = multi_question_violations
        
        # Check conversation flow quality
        analysis["avg_doctor_message_length"] = sum(len(m['content']) for m in doctor_messages) / len(doctor_messages) if doctor_messages else 0
        analysis["avg_patient_message_length"] = sum(len(m['content']) for m in patient_messages) / len(patient_messages) if patient_messages else 0
        
        return analysis
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report of all conversations."""
        df = self.load_conversations()
        
        if df.empty:
            return {"error": "No conversations found"}
        
        report = {
            "overview": {
                "total_conversations": len(df),
                "date_range": {
                    "earliest": df['start_time'].min(),
                    "latest": df['start_time'].max()
                }
            }
        }
        
        # Completion status analysis
        completion_stats = df['completion_status'].value_counts().to_dict()
        report["completion_analysis"] = {
            "status_distribution": completion_stats,
            "completion_rate": completion_stats.get('completed', 0) / len(df) * 100
        }
        
        # Urgency level analysis
        urgency_stats = df['urgency_level'].value_counts().to_dict()
        report["urgency_analysis"] = {
            "urgency_distribution": urgency_stats,
            "high_urgency_rate": urgency_stats.get('high', 0) / len(df) * 100
        }
        
        # High-risk patient analysis
        high_risk_count = sum(1 for flags in df['high_risk_flags'] if flags)
        report["risk_analysis"] = {
            "high_risk_patients": high_risk_count,
            "high_risk_rate": high_risk_count / len(df) * 100,
            "risk_flag_distribution": {}
        }
        
        # Collect all risk flags
        all_flags = []
        for flags in df['high_risk_flags']:
            all_flags.extend(flags)
        
        from collections import Counter
        flag_counts = Counter(all_flags)
        report["risk_analysis"]["risk_flag_distribution"] = dict(flag_counts)
        
        # Epworth score analysis
        epworth_scores = df['epworth_score'].dropna()
        if not epworth_scores.empty:
            report["epworth_analysis"] = {
                "mean_score": epworth_scores.mean(),
                "median_score": epworth_scores.median(),
                "high_risk_scores": sum(1 for score in epworth_scores if score > 20),
                "score_distribution": {
                    "normal (0-7)": sum(1 for score in epworth_scores if 0 <= score <= 7),
                    "mild (8-9)": sum(1 for score in epworth_scores if 8 <= score <= 9),
                    "moderate (10-15)": sum(1 for score in epworth_scores if 10 <= score <= 15),
                    "severe (16-24)": sum(1 for score in epworth_scores if 16 <= score <= 24)
                }
            }
        
        # Patient profile analysis
        primary_complaints = [profile['primary_complaint'] for profile in df['patient_profile']]
        complaint_counts = Counter(primary_complaints)
        report["patient_analysis"] = {
            "complaint_distribution": dict(complaint_counts),
            "unique_patients": len(set(df['patient_name']))
        }
        
        # Conversation quality analysis
        quality_scores = []
        for conv_id in df['conversation_id']:
            quality = self.analyze_conversation_quality(conv_id)
            if 'error' not in quality:
                quality_scores.append(quality)
        
        if quality_scores:
            report["quality_analysis"] = {
                "epworth_coverage_rate": sum(1 for q in quality_scores if q['epworth_coverage']) / len(quality_scores) * 100,
                "psqi_coverage_rate": sum(1 for q in quality_scores if q['psqi_coverage']) / len(quality_scores) * 100,
                "risk_screening_rate": sum(1 for q in quality_scores if q['risk_screening']) / len(quality_scores) * 100,
                "single_question_adherence_rate": sum(1 for q in quality_scores if q['single_question_adherence']) / len(quality_scores) * 100,
                "avg_conversation_balance": sum(q['conversation_balance'] for q in quality_scores) / len(quality_scores),
                "avg_total_messages": sum(q['total_messages'] for q in quality_scores) / len(quality_scores)
            }
        
        return report
    
    def print_detailed_report(self):
        """Print a detailed analysis report."""
        report = self.generate_summary_report()
        
        if "error" in report:
            print(f"❌ Error: {report['error']}")
            return
        
        print("🏥 SLEEP CONSULTATION AGENT EVALUATION REPORT")
        print("=" * 60)
        
        # Overview
        overview = report["overview"]
        print(f"\n📊 OVERVIEW:")
        print(f"   Total conversations: {overview['total_conversations']}")
        print(f"   Date range: {overview['date_range']['earliest']} to {overview['date_range']['latest']}")
        
        # Completion Analysis
        completion = report["completion_analysis"]
        print(f"\n✅ COMPLETION ANALYSIS:")
        print(f"   Completion rate: {completion['completion_rate']:.1f}%")
        print(f"   Status distribution:")
        for status, count in completion['status_distribution'].items():
            print(f"      {status}: {count}")
        
        # Urgency Analysis
        urgency = report["urgency_analysis"]
        print(f"\n🚨 URGENCY ANALYSIS:")
        print(f"   High urgency rate: {urgency['high_urgency_rate']:.1f}%")
        print(f"   Urgency distribution:")
        for level, count in urgency['urgency_distribution'].items():
            print(f"      {level}: {count}")
        
        # Risk Analysis
        risk = report["risk_analysis"]
        print(f"\n⚠️  HIGH-RISK PATIENT ANALYSIS:")
        print(f"   High-risk patients: {risk['high_risk_patients']} ({risk['high_risk_rate']:.1f}%)")
        if risk['risk_flag_distribution']:
            print(f"   Risk flag distribution:")
            for flag, count in risk['risk_flag_distribution'].items():
                print(f"      {flag}: {count}")
        
        # Epworth Analysis
        if "epworth_analysis" in report:
            epworth = report["epworth_analysis"]
            print(f"\n😴 EPWORTH SLEEPINESS SCALE ANALYSIS:")
            print(f"   Mean score: {epworth['mean_score']:.1f}")
            print(f"   Median score: {epworth['median_score']:.1f}")
            print(f"   High-risk scores (>20): {epworth['high_risk_scores']}")
            print(f"   Score distribution:")
            for category, count in epworth['score_distribution'].items():
                print(f"      {category}: {count}")
        
        # Patient Analysis
        patient = report["patient_analysis"]
        print(f"\n👥 PATIENT ANALYSIS:")
        print(f"   Unique patients: {patient['unique_patients']}")
        print(f"   Complaint distribution:")
        for complaint, count in patient['complaint_distribution'].items():
            print(f"      {complaint}: {count}")
        
        # Quality Analysis
        if "quality_analysis" in report:
            quality = report["quality_analysis"]
            print(f"\n🎯 CONVERSATION QUALITY ANALYSIS:")
            print(f"   Epworth coverage rate: {quality['epworth_coverage_rate']:.1f}%")
            print(f"   PSQI coverage rate: {quality['psqi_coverage_rate']:.1f}%")
            print(f"   Risk screening rate: {quality['risk_screening_rate']:.1f}%")
            print(f"   Single question adherence: {quality['single_question_adherence_rate']:.1f}%")
            print(f"   Average conversation balance: {quality['avg_conversation_balance']:.2f}")
            print(f"   Average total messages: {quality['avg_total_messages']:.1f}")
    
    def export_detailed_conversation(self, conversation_id: str, output_file: str = None):
        """Export a detailed view of a specific conversation."""
        df = self.load_conversations()
        conv_data = df[df['conversation_id'] == conversation_id]
        
        if conv_data.empty:
            print(f"❌ Conversation {conversation_id} not found")
            return
        
        messages = self.get_conversation_messages(conversation_id)
        quality = self.analyze_conversation_quality(conversation_id)
        
        conv_info = conv_data.iloc[0]
        
        output = []
        output.append(f"🏥 DETAILED CONVERSATION ANALYSIS")
        output.append(f"=" * 50)
        output.append(f"Conversation ID: {conversation_id}")
        output.append(f"Patient: {conv_info['patient_name']}")
        output.append(f"Primary Complaint: {conv_info['patient_profile']['primary_complaint']}")
        output.append(f"Start Time: {conv_info['start_time']}")
        output.append(f"End Time: {conv_info['end_time']}")
        output.append(f"Completion Status: {conv_info['completion_status']}")
        output.append(f"Urgency Level: {conv_info['urgency_level']}")
        output.append(f"Epworth Score: {conv_info['epworth_score']}")
        output.append(f"High-Risk Flags: {', '.join(conv_info['high_risk_flags']) if conv_info['high_risk_flags'] else 'None'}")
        output.append("")
        
        # Quality metrics
        output.append(f"📊 QUALITY METRICS:")
        output.append(f"   Total messages: {quality['total_messages']}")
        output.append(f"   Conversation balance: {quality['conversation_balance']:.2f}")
        output.append(f"   Epworth coverage: {'✅' if quality['epworth_coverage'] else '❌'}")
        output.append(f"   PSQI coverage: {'✅' if quality['psqi_coverage'] else '❌'}")
        output.append(f"   Risk screening: {'✅' if quality['risk_screening'] else '❌'}")
        output.append(f"   Single question adherence: {'✅' if quality['single_question_adherence'] else '❌'}")
        output.append("")
        
        # Conversation transcript
        output.append(f"💬 CONVERSATION TRANSCRIPT:")
        output.append("-" * 50)
        
        for msg in messages:
            sender_icon = "🤖" if msg['sender'] == 'doctor' else "👤"
            output.append(f"{sender_icon} {msg['sender'].title()}: {msg['content']}")
            output.append("")
        
        # Summaries
        if conv_info['doctor_summary']:
            output.append(f"📋 DOCTOR SUMMARY:")
            output.append(conv_info['doctor_summary'])
            output.append("")
        
        if conv_info['patient_summary']:
            output.append(f"👤 PATIENT SUMMARY:")
            output.append(conv_info['patient_summary'])
            output.append("")
        
        # Output to file or print
        content = "\n".join(output)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"📄 Detailed conversation exported to: {output_file}")
        else:
            print(content)

def main():
    """Main function for conversation evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate sleep consultation conversations")
    parser.add_argument("--db", "-d", type=str, required=True,
                       help="Path to conversation results database")
    parser.add_argument("--conversation-id", "-c", type=str, default=None,
                       help="Analyze specific conversation ID")
    parser.add_argument("--export", "-e", type=str, default=None,
                       help="Export detailed conversation to file")
    parser.add_argument("--summary", "-s", action="store_true",
                       help="Show summary report (default)")
    
    args = parser.parse_args()
    
    try:
        evaluator = ConversationEvaluator(args.db)
        
        if args.conversation_id:
            # Analyze specific conversation
            evaluator.export_detailed_conversation(args.conversation_id, args.export)
        else:
            # Show summary report
            evaluator.print_detailed_report()
            
    except Exception as e:
        print(f"❌ Error during evaluation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()