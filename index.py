
import flask
from flask import Flask, render_template
from flask_bootstrap import Bootstrap


import os
import json
import httplib2
import requests
import urllib


from apiclient import discovery
from oauth2client import client




app = Flask(__name__)
bootstrap = Bootstrap(app)


lambdaUrl1 = 'https://bfwrh01vul.execute-api.us-east-1.amazonaws.com/prod/users'
lambdaUrl2 = 'https://bfwrh01vul.execute-api.us-east-1.amazonaws.com/prod/handleStatic'
lambdaUrl3 = 'https://bfwrh01vul.execute-api.us-east-1.amazonaws.com/prod/fileAssociation'
credentials = client.Flow()

response = []


@app.route("/")
def index():
	return "You are in ROOT "



@app.route('/oauth2callback')
def oauth2callback():	
  flow = client.flow_from_clientsecrets(
      'client_secrets.json',
      scope='https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/admin.directory.user',
      redirect_uri=flask.url_for('oauth2callback', _external=True)
      )
  flow.params['access_type'] = 'offline'

  #flow.params['include_granted_scopes'] = True
  if 'code' not in flask.request.args:
    auth_uri = flow.step1_get_authorize_url()
    return flask.redirect(auth_uri)
  else:
    auth_code = flask.request.args.get('code')

    global credentials
    credentials = flow.step2_exchange(auth_code)

    http = credentials.authorize(httplib2.Http())
    users = discovery.build('admin', 'directory_v1', http=http).users().list(customer='my_customer', maxResults=10, orderBy='email').execute()
    print (users['users'])
    postToAWSLambda(users)         
 
        
    #delegated_credentials = credentials.create_delegated('bhanu.mallya@adya.io')

    #flask.session['credentials'] = credentials.to_json()
    return flask.redirect(flask.url_for('getPermList'))



def postToAWSLambda(users):

 for user in users:
	   fullName = user['name']['fullName']
	   name = user['name']['givenName']
	   email = user['emails'][0]['address']
	   account = 'adya'
	   data = {'user_name': fullName, 'user_id': email, 'account': account}
	   http = httplib2.Http()
	   headers = {'Content-type': 'application/json', "Accept": "*/*"}
	   print 'Sending post request to:', lambdaUrl1, ',Data: ', data
	   r = requests.post(lambdaUrl1, data=json.dumps(data), headers=headers)
	   print r




@app.route("/getPermList")
def getPermList():
	http = credentials.authorize(httplib2.Http())
	service = discovery.build('drive', 'v3', http=http)

	#abt = service.about().get(fields="user, storageQuota").execute()
	#print (abt)

	dirs = ["root"]

	aitems = []

	for dir in dirs:
		results = service.files().list(q="'" + dir + "' in parents and trashed=false").execute()
		items = results.get('files', [])

		for item in items:
			driveItem = service.files().get(fileId=item['id']).execute()
			mimeType = driveItem['mimeType']
			index = 0 
			try:
				index = mimeType.rindex(".")
			except:
				try:
					index = mimeType.rindex("/")
				except:
					index = 0

			fileType =  mimeType[index+1:]
			print(dirs)

			if len(dirs) < 3 and mimeType.endswith("folder"):
				dirs.append(item['id'])

			aitem = {'id': item['id'], 'name': item['name'], 'type': fileType}
			permList = service.permissions().list(fileId=item['id']).execute()
			perms = []
			for perm in permList.get('permissions', []):
				pp = service.permissions().get(fileId=item['id'], permissionId=perm['id'], fields="type, domain, emailAddress, role").execute()
				try:
					aperm = {"role" : pp['role'], "email" : pp['emailAddress']}
					perms.append(aperm)
				except:
					print("exception ", pp)
			aitem['perms'] = perms
			aitems.append(aitem)
			postToAwsLambda1(aitems)
			postToAwsLambda2(aitems)



	return render_template('index.html', items=aitems)

def postToAwsLambda1(aitems):
	for item in aitems:
		resource_id = item['name']
		resource_type = item['type']
		account = "adya"
		permissions = []
		for k in item['perms']:
			permission = {"user_id": k['email'], "access": k['role']}
			permissions.append(permission)
		data_source = "google_drive"
		data = {'resource_id': resource_id, 'resource_type':resource_type, 'account': account  , 'data_source': data_source , 'permission' : permission}
		headers = {'Content-type': 'application/json', "Accept": "*/*"}
		print 'Sending post request to:', lambdaUrl2, ',Data: ', data
		s = requests.post(lambdaUrl2, data=json.dumps(data), headers=headers)
		print s

def postToAwsLambda2(aitems):
	for item1 in aitems:
		file_id = item1['id']
		file_name = item1['name']
		file_type = item1['type']
		data = {'file_id':file_id, 'file_name':file_name , 'file_type':file_type}
		headers = {'Content-type': 'application/json', "Accept": "*/*"}
		print 'Sending post request to:', lambdaUrl3, ',Data: ', data
		x = requests.post(lambdaUrl3, data=json.dumps(data), headers=headers)
		print x




if __name__ == '__main__':
	port = int(os.environ.get('port', 5000))
	app.run(host='0.0.0.0', port=port, debug=True)


