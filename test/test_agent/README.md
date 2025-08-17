# Sleep Consultation Agent Testing Framework

This testing framework provides automated conversation testing between patient simulators and the sleep consultation agent. It includes realistic patient personas, conversation orchestration, and comprehensive evaluation tools.

## 🏗️ Architecture

- **`patient_simulator.py`**: Creates realistic patient personas with various sleep disorders
- **`conversation_orchestrator.py`**: Manages conversations between patient simulator and sleep agent
- **`run_conversations.py`**: Main script to execute multiple automated conversations
- **`evaluate_conversations.py`**: Comprehensive evaluation and analysis framework

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"
```

### 2. Run Conversations

```bash
# Run 5 conversations (default)
python test/test_agent/run_conversations.py

# Run 10 conversations with custom settings
python test/test_agent/run_conversations.py --num-conversations 10 --max-turns 60

# Specify custom output database
python test/test_agent/run_conversations.py -n 5 -o my_results.db
```

### 3. Evaluate Results

```bash
# View summary report
python test/test_agent/evaluate_conversations.py --db test/test_agent/conversation_results.db

# Analyze specific conversation
python test/test_agent/evaluate_conversations.py --db conversation_results.db --conversation-id conv_12345_Sarah_Johnson

# Export detailed conversation to file
python test/test_agent/evaluate_conversations.py --db conversation_results.db --conversation-id conv_12345_Sarah_Johnson --export detailed_conversation.txt
```

## 👥 Patient Personas

The framework includes 5 diverse patient profiles:

### 1. Sarah Johnson (34, Software Engineer)
- **Primary Complaint**: Insomnia
- **Key Symptoms**: Difficulty falling asleep, multiple night wakings, daytime fatigue
- **Epworth Score**: 13 (moderate sleepiness)
- **Risk Factors**: High work stress, late screen time

### 2. Michael Chen (45, Truck Driver) ⚠️ HIGH RISK
- **Primary Complaint**: Excessive daytime sleepiness
- **Key Symptoms**: Falling asleep while driving, loud snoring, morning headaches
- **Epworth Score**: 22 (severe sleepiness - HIGH RISK)
- **Risk Factors**: Safety-sensitive occupation, cardiovascular comorbidities

### 3. Emma Rodriguez (28, Nurse - Night Shifts)
- **Primary Complaint**: Shift work sleep disorder
- **Key Symptoms**: Difficulty sleeping during day, extreme fatigue during night shifts
- **Epworth Score**: 16 (severe sleepiness)
- **Risk Factors**: Healthcare worker, irregular sleep schedule

### 4. Robert Williams (52, Pilot) ⚠️ HIGH RISK
- **Primary Complaint**: Sudden muscle weakness episodes (cataplexy)
- **Key Symptoms**: Muscle weakness when laughing, sleep paralysis, excessive sleepiness
- **Epworth Score**: 22 (severe sleepiness - HIGH RISK)
- **Risk Factors**: Safety-sensitive occupation, suspected narcolepsy

### 5. Lisa Thompson (38, Teacher)
- **Primary Complaint**: Restless legs and poor sleep
- **Key Symptoms**: Uncomfortable leg sensations, urge to move legs, partner reports movements
- **Epworth Score**: 7 (normal range)
- **Risk Factors**: History of iron deficiency

## 📊 Evaluation Metrics

The evaluation framework analyzes:

### Conversation Quality
- **Epworth Coverage**: Whether all 8 Epworth situations were assessed
- **PSQI Coverage**: Whether PSQI components were covered for insomnia patients
- **Risk Screening**: Assessment of high-risk symptoms and safety concerns
- **Single Question Adherence**: Whether doctor asked one question at a time
- **Conversation Balance**: Ratio of patient to doctor messages

### Clinical Outcomes
- **Completion Rate**: Percentage of conversations that reached natural conclusion
- **High-Risk Detection**: Identification of patients requiring urgent attention
- **Urgency Classification**: Distribution of routine/moderate/high urgency cases
- **Epworth Score Analysis**: Distribution and high-risk score detection

### Patient Safety
- **Driving Safety Assessment**: Detection of drowsy driving concerns
- **Occupational Safety**: Screening for safety-sensitive jobs
- **Cataplexy Detection**: Identification of sudden muscle weakness
- **Mental Health Impact**: Assessment of psychological effects

## 🗄️ Database Schema

### Conversations Table
- `conversation_id`: Unique identifier
- `patient_name`: Patient persona name
- `patient_profile`: JSON of complete patient data
- `start_time`/`end_time`: Conversation timestamps
- `doctor_summary`/`patient_summary`: Generated summaries
- `urgency_level`: Clinical urgency assessment
- `epworth_score`: Calculated Epworth Sleepiness Scale score
- `high_risk_flags`: JSON array of identified risk factors
- `completion_status`: How conversation ended

### Messages Table
- `conversation_id`: Links to conversations
- `message_order`: Sequential message number
- `sender`: 'doctor' or 'patient'
- `message_content`: Full message text
- `timestamp`: Message timestamp

## 🎯 Usage Examples

### Basic Testing
```bash
# Quick test with 3 conversations
python test/test_agent/run_conversations.py -n 3

# View results
python test/test_agent/evaluate_conversations.py -d test/test_agent/conversation_results.db
```

### Comprehensive Testing
```bash
# Extended testing session
python test/test_agent/run_conversations.py --num-conversations 20 --max-turns 75

# Detailed analysis
python test/test_agent/evaluate_conversations.py -d conversation_results.db -s
```

### Specific Conversation Analysis
```bash
# List all conversations first
sqlite3 conversation_results.db "SELECT conversation_id, patient_name, completion_status FROM conversations;"

# Analyze specific conversation
python test/test_agent/evaluate_conversations.py -d conversation_results.db -c conv_1234567890_Michael_Chen

# Export to file for detailed review
python test/test_agent/evaluate_conversations.py -d conversation_results.db -c conv_1234567890_Michael_Chen -e michael_conversation.txt
```

## 🔧 Configuration Options

### run_conversations.py Options
- `--num-conversations, -n`: Number of conversations to run (default: 5)
- `--max-turns, -t`: Maximum turns per conversation (default: 50)
- `--output-db, -o`: Output database path
- `--api-key, -k`: OpenAI API key (or use environment variable)

### evaluate_conversations.py Options
- `--db, -d`: Path to conversation results database (required)
- `--conversation-id, -c`: Analyze specific conversation ID
- `--export, -e`: Export detailed conversation to file
- `--summary, -s`: Show summary report (default)

## 📈 Expected Results

A well-functioning sleep consultation agent should achieve:

- **Completion Rate**: >90%
- **Epworth Coverage**: >95% (mandatory questionnaire)
- **Risk Screening**: >90% (safety assessment)
- **Single Question Adherence**: >95% (interaction pattern)
- **High-Risk Detection**: 100% for patients with Epworth >20 or safety concerns

## 🚨 High-Risk Patient Identification

The system should flag these scenarios:
- Epworth sleepiness score >20
- Falling asleep while driving
- Safety-sensitive occupations with sleepiness
- Frequent cataplexy episodes
- Dangerous sleepwalking behaviors
- Significant mental health impact

## 🔍 Troubleshooting

### Common Issues

1. **API Key Error**: Ensure OPENAI_API_KEY is set in environment
2. **Import Errors**: Check that src/ directory is in Python path
3. **Database Locked**: Close any open database connections
4. **Conversation Timeout**: Increase max-turns if conversations are cut short

### Debug Mode
Add debug prints to conversation_orchestrator.py for detailed logging:
```python
print(f"Debug: Current state = {current_state.values}")
```

## 📝 Contributing

To add new patient personas:
1. Add profile to `patient_simulator.py` in `_create_patient_profiles()`
2. Include realistic Epworth responses
3. Add appropriate risk factors
4. Test with single conversation first

To modify evaluation metrics:
1. Update `analyze_conversation_quality()` in `evaluate_conversations.py`
2. Add new indicators or thresholds
3. Update summary report generation