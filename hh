#test

##Question 1
# a=[1,2,3,4,5,6,7,8]
# def evennumber(a):
#     b=[i for i in a if i%2==0]
#     return sorted(b,reverse=True)

# print (evennumber(a))

##Question2
# employee=("john","doe",35,"Manager")
# fnam,lname,age,desig=employee
# print(f"fname:{fnam},lname:{lname},age;{age},desig:{desig}")

##Question3
# set1={1,2,3,4}
# set2={3,4,5,6}
# print(f"commomn element {set1 & set2}")
# print(f"unique element s1 {set1.difference(set2)}")

##Q4
# student=[{"name":"Mohit","Score":10},{"name":"Mohit1","Score":20},{"name":"Mohit3","Score":30},{"name":"Mohit4","Score":40}]
# def findscore(name):
#     c=0
#     try:
#         for i in student:
#             if(i["name"]==name):
#                 c=1
#                 print(f"{name} score is {i["Score"]}")
#                 break
#         if c==0:
#             print("Not found")
#     except  Exception as e:
#         print(f"Some error occured: {e}")

# name=input("enter name")
# findscore(name)

##Question5
# userin=input("enter a integer value: ")
# try :
#     if int(userin)>0:
#         print("+ve")
#     elif int(userin)==0:
#         print("zero")
#     elif int(userin)>0:
#          print("-ve")
# except Exception as e:
#     print ("Not int")
      
##Q6
# student=[{"name":"Mohit","Score":10},{"name":"Mohit1","Score":20},{"name":"Mohit3","Score":30},{"name":"Mohit4","Score":40}]
# for i in student:
#     print(f"Product:{i["name"]},Price:{i["Score"]}")

#Q7

# userin1=input("enter a integer value: ")
# userin2=input("enter a integer value: ")
# try :
#     n1=int(userin1)
#     n2=int(userin2)
#     print(f" Division{n1/n2}")
# except Exception as e:
#     print (e)


##Q8
#k=[i*i for i in range(1,20) if i%2!=0]
#print(k)
##Q10
# for i in k:
#     if i%7==0:
#         break
#     else:
#         print(i)

#Q11
# num=[1,3,4,2,5,7,3,2,1,2]
# occurance={}
# for i in num:
#     if i in occurance:
#         occurance[i]+=1
#     else:
#         occurance[i]=1
#     print(occurance)
# print(occurance)

###Q9

# import pandas as pd
# data={'Name':['Alice','bob','charlie'],
#       'Age':[25,30,35],
#       'Depart':["hr",'it','Finance']      
#       }
# df=pd.DataFrame(data)
# print(df.head(2))
# print(df[['Name','Depart']])
# print(df[df['Age']==30])
