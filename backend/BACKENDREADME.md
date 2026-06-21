## Random Forest Training Result
Metric	            Result
Training rows	    40,762
Testing rows	    10,190
Features	        34
Accuracy	        99.96%
Fraud precision	    100.00%
Fraud recall	    98.60%
Fraud F1-score	    99.30%
ROC-AUC	            0.9999986
PR-AUC              0.9999510

## LightGBM Training Result
Metric	        	    LightGBM
Accuracy        	    99.94%
Fraud precision     	98.61%
Fraud recall        	99.30%
Fraud F1-score      	98.95%
ROC-AUC         	    0.9999940
PR-AUC          	    0.9997938
False positives 	    4
Missed frauds   	    2

## Model Comparison
Metric	            Random Forest	        LightGBM        V2 Tuned Calibrated LightGBM
Accuracy	        99.96%	                99.94%
Fraud precision	    100.00%	                98.61%
Fraud recall	    98.60%	                99.30%
Fraud F1-score	    99.30%	                98.95%
ROC-AUC	            0.9999986	            0.9999940
PR-AUC	            0.9999510	            0.9997938
False positives	    0	                    4
Missed frauds	    4	                    2

Inference from model comparison table
Random Forest was more conservative:
False fraud alerts: 0
Missed frauds: 4

LightGBM caught slightly more fraud:
False fraud alerts: 4
Missed frauds: 2

## Trade-off:
Random Forest gives fewer false alarms.
LightGBM catches more fraud.
Both models are extremely strong on this synthetic dataset.

For a fraud detection system, we sould choose LightGBM if our priority is catching as much fraud as possible, because it missed only 2 fraud cases instead of 4.

We sould choose Random Forest if our priority is avoiding false accusations, because it produced 0 false positives.

## Feature Importance Difference

Random Forest’s top features were:
seconds_since_last_txn
cross_border
txn_count_1h
enriched_amount_usd
authentication_enc

LightGBM’s top features were:
enriched_amount_usd
seconds_since_last_txn
transaction_country_fraud_rate
authentication_enc
cross_border

Both models agree that amount, transaction timing, geography, and authentication are important fraud signals.

## Calibrated LightGBM result
Full training rows: 40762
Final testing rows: 10190
Number of features: 34

Model training rows: 32609
Calibration rows: 8153

Confusion Matrix at 0.50 threshold:
[[9903    1]
 [   1  285]]

Classification Report at 0.50 threshold:
              precision    recall  f1-score   support

           0     0.9999    0.9999    0.9999      9904
           1     0.9965    0.9965    0.9965       286

    accuracy                         0.9998     10190
   macro avg     0.9982    0.9982    0.9982     10190
weighted avg     0.9998    0.9998    0.9998     10190

ROC-AUC: 0.9999992939209418
PR-AUC: 0.9999755915242867

Decision Thresholds:
{
  "APPROVE": "score < 0.011088",
  "APPROVE_WITH_REVIEW": "0.011088 <= score < 0.994687",
  "DECLINE": "score >= 0.994687"
}

Decision Distribution:
decision
APPROVE                9903
DECLINE                 284
APPROVE_WITH_REVIEW       3
Name: count, dtype: int64

Fraud Rate by Decision:
decision
APPROVE                0.000000
APPROVE_WITH_REVIEW    0.666667
DECLINE                1.000000
Name: is_fraud, dtype: float64

Fraud Count by Decision:
decision
APPROVE                  0
APPROVE_WITH_REVIEW      2
DECLINE                284
Name: is_fraud, dtype: int64
Model saved to: \backend\ml\artefacts\fraud_model.pkl
Feature schema saved to: \backend\ml\artefacts\feature_schema.json


## Tuned Calibrated LightGBM Version 2 result

Dataset version: version2  
Full training rows: 64762  
Final testing rows: 16190  
Number of features: 32  

Model training rows:  45333  
Validation rows:      9714  
Calibration rows:     9715  

Best validation PR-AUC: 0.750377  

Best parameters:
{
  "subsample": 0.8,
  "reg_lambda": 5.0,
  "reg_alpha": 0.1,
  "num_leaves": 15,
  "n_estimators": 300,
  "min_child_samples": 100,
  "max_depth": 12,
  "learning_rate": 0.08,
  "colsample_bytree": 0.8
}

Confusion Matrix at 0.50 threshold:
[[15540   116]
 [  219   315]]

Classification Report at 0.50 threshold:
              precision    recall  f1-score   support

           0     0.9861    0.9926    0.9893     15656
           1     0.7309    0.5899    0.6528       534

    accuracy                         0.9793     16190
   macro avg     0.8585    0.7912    0.8211     16190
weighted avg     0.9777    0.9793    0.9782     16190

ROC-AUC: 0.9656550766574995
PR-AUC: 0.720934490295165

Decision Thresholds:
{
  "APPROVE": "score < 0.016541",
  "APPROVE_WITH_REVIEW": "0.016541 <= score < 0.592932",
  "DECLINE": "score >= 0.592932"
}

Decision Distribution:
decision
APPROVE                14321
APPROVE_WITH_REVIEW     1577
DECLINE                  292
Name: count, dtype: int64

Fraud Rate by Decision:
decision
APPROVE                0.004120
APPROVE_WITH_REVIEW    0.140774
DECLINE                0.866438
Name: is_fraud, dtype: float64

Fraud Count by Decision:
decision
APPROVE                 59
APPROVE_WITH_REVIEW    222
DECLINE                253
Name: is_fraud, dtype: int64

Tuned model saved to: \backend\ml\artefacts\version2\fraud_model_tuned.pkl
Tuned feature schema saved to: \backend\ml\artefacts\version2\feature_schema_tuned.json
Tuning results saved to: \backend\ml\artefacts\version2\tuning_results_v2.csv
Best params saved to: \backend\ml\artefacts\version2\best_params_v2.json