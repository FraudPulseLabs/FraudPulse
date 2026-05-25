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
Metric	            Random Forest	        LightGBM
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

## Version 2 Result Summary

Metric	              Version 2 Calibrated LightGBM
Training rows	        64,762
Model training rows	  51,809
Calibration rows	    12,953
Test rows	            16,190
Feature count	        32
Train fraud cases	    2,074
Test fraud cases	    534
Accuracy	            97.90%
Fraud precision	      71.27%
Fraud recall	        60.86%
Fraud F1-score	      65.66%
ROC-AUC	              0.9611
PR-AUC	              0.7169


## Confusion Matrix
[[15525   131]
 [  209   325]]
Meaning:
15,525 legitimate transactions correctly approved/classified as non-fraud.
131 legitimate transactions wrongly flagged as fraud.
209 fraud transactions missed.
325 fraud transactions caught.


## Thresholds
APPROVE: score < 0.007463
APPROVE_WITH_REVIEW: 0.007463 <= score < 0.703817
DECLINE: score >= 0.703817

## Decision Distribution
Decision	              Count	    Fraud Count	    Fraud Rate
APPROVE	                13,970	       57	          0.41%
APPROVE_WITH_REVIEW	    1,963	        245	          12.48%
DECLINE	                257	          232	          90.27%


Loaded model:     calibrated_lightgbm_version2
Dataset version:  version2
Feature count:    32
Actual label:     1
Fraud score:      0.668557
Decision:         APPROVE_WITH_REVIEW

## Comparison With Version 1

Metric	              Version 1	                    Version 2
Training rows	          40,762	                      64,762
Test rows	              10,190	                      16,190
Feature count	            34	                          32
Train fraud cases	       1,356	                      2,074
Test fraud cases	        286	                         534
Accuracy	                99.98%	                    97.90%
Fraud precision	          99.65%	                    71.27%
Fraud recall	            99.65%	                    60.86%
Fraud F1-score	          99.65%	                    65.66%
ROC-AUC	                  0.9999993	                  0.9611
PR-AUC	                  0.9999756	                  0.7169

The Comparison table above shows that Version 2 is more realistic and harder than Version 1.

Version 1 was almost perfectly separable. Version 2 has weaker performance, which usually means the new dataset is less “easy” and may better reflect realistic fraud detection challenges.

Version 2 produced lower but more realistic fraud detection performance compared with Version 1. The calibrated LightGBM model still achieved strong ranking performance with ROC-AUC of 0.9611, but fraud recall and precision dropped, showing that the updated dataset is more challenging and may require further feature tuning or threshold adjustment.
