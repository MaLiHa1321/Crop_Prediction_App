import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

import pickle

data = pd.read_csv(r"D:\Flask Project\crop_prediction\Crop_recommendation.csv")

data.head(5)
data.shape
data.isnull().sum()
x = data.iloc[:,:-1] 
y = data.iloc[:,-1] 

X_train, X_test,y_train,y_test = train_test_split(x,y,test_size=0.2,random_state=42)
X_train.head()
y_train.head()

model = RandomForestClassifier()
model.fit(X_train,y_train)

pickle.dump(model, open("model.pkl", "wb"))
prediction = model.predict(X_test)

accuracy = model.score(X_test,y_test)

print("Accuracy:", accuracy)