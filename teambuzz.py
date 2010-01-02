# Big To Do list:
# PC applications
# PC review and approval process
# PC project assignments
# PC UI on My TEAMBuzz (view list of people in project, send them all an email, etc)

# Group creation
# Group management UI

# Admin tools!
# Adding projects
# Shuffling people around


# Specific TODOs
# TODO: send password upon account creation
# TODO: client-side form validation. JQuery will make this easyish
# TODO: change the email address to a correct on on the dev server
# TODO: on failed forms, fill in the old values
# TODO: slots calculation using group slots


import cgi
import os
import logging
import gmemsess
import md5
import random
import admin
import datetime

from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext.db import djangoforms

EMAIL_FROM = "admin@teambuzz.org"
ROOT_URL = "http://main.teambuzz.org/"
GREEK_AFFS = set(['Not Affiliated','Alpha Epsilon Pi',
'Alpha Phi',
'Alpha Phi Alpha',
'Alpha Tau Omega',
'Beta Theta Pi',
'Chi Psi',
'Delta Chi',
'Delta Sigma Phi',
'Delta Tau Delta',
'Delta Upsilon',
'Kappa Alpha',
'Kappa Sigma',
'Lambda Chi Alpha',
'Phi Delta Theta',
'Phi Gamma Delta',
'Phi Kappa Psi',
'Phi Kappa Sigma',
'Phi Kappa Tau',
'Phi Kappa Theta',
'Phi Sigma Kappa',
'Pi Kappa Alpha',
'Pi Kappa Phi',
'Psi Upsilon',
'Sigma Chi',
'Sigma Nu',
'Sigma Phi Epsilon',
'Tau Kappa Epsilon',
'Theta Chi',
'Theta Xi',
'Alpha Chi Omega',
'Alpha Delta Pi',
'Alpha Gamma Delta',
'Alpha Xi Delta',
'Lambda Theta Alpha',
'Chi Omega Tau',
'Phi Mu',
'Zeta Tau Alpha',
'Lambda Nu',
'Alpha Delta Chi',
'Alpha Phi Omega',
'Alpha Kappa Alpha',
'Delta Sigma Theta',
'Alpha Omega Epsilon',
'Sigma Alpha Epsilon',
'Zeta Beta Tau'])

#CONFIRM_URL = 'http://main.teambuzz.org/confirm'
#CONFIRM_URL = 'http://localhost:8080/confirm'

# ----------------------------------------
#
# Utility functions
#
#
# ----------------------------------------

def renderPageHelper(self, filename, template_values = {}, include_session_data = True):
	sess=gmemsess.Session(self)
	user_data = {'user': sess['current_user'] if 'current_user' in sess else None}
	
	template_values.update(user_data)
		
	path = os.path.join(os.path.dirname(__file__), filename)
	self.response.out.write(template.render(path, template_values))

def updateSessionForLogin(self, username):
	sess=gmemsess.Session(self)
	sess['current_user'] = username
	sess.save()

def getPhasesForDate(date):
	""" returns a list of names of the phases for the current date """
	ret = []
	for p in Phase.all():
		if p.start_date <= date and p.end_date >= date:
			ret.append(p.name)
	return ret
	
def getPhasesForRightNow():
	return getPhasesForDate(datetime.date.today())
	
def inPhase(phase_name):
	return phase_name in getPhasesForRightNow()
	
def errorRedirect(self, message):
	self.redirect("/error?message=" + message)

# ----------------------------------------
#
# Model classes
#
#
# ----------------------------------------
class Phase(db.Model):
	name = db.StringProperty()
	start_date = db.DateProperty()
	end_date = db.DateProperty()
	description = db.StringProperty()

class Greek(db.Model):
	name = db.StringProperty()

class Project(db.Model):
	name = db.StringProperty()
	max_volunteers = db.IntegerProperty()
	description = db.StringProperty(multiline=True)
	location = db.StringProperty()
	type_of_work = db.StringProperty(choices = ['Indoor', 'Outdoor', 'Children', 'Fun'], default='Fun')
	spots_taken = None
	spots_remaining = None
	available = None
	
	def getForm(self):
		return Projec
	
	def canJoin(self):
		self.calculateSpots()
		return self.available
	
	def calculateSpots(self):
		self.spots_taken = 0
		if inPhase("group_registration"):
			users = User.gql("WHERE project=:1 and pending=false", self)
			for u in users:
				if u.group is None:
					self.spots_taken+=1
			groups = Group.gql("WHERE project=:1 and pending=false", self)
			for g in groups:
				self.spots_taken += g.slots
		else:
			self.spots_taken = User.gql("WHERE project=:1 and pending=false", self).count()
		
		self.spots_remaining = self.max_volunteers - self.spots_taken
		self.available = (self.spots_remaining > 0)

class Group(db.Model):
	name = db.StringProperty()
	password = db.StringProperty()
	project = db.ReferenceProperty(Project)
	slots = db.IntegerProperty()
	spots_taken = None
	spots_remaining = None
	pending = db.BooleanProperty(default=False)
	
	def calculateSpots(self):
		self.spots_taken = self.spotsTaken()
		self.spots_remaining = self.slots - self.spots_taken
	
	def spotsTaken(self):
		return User.gql("WHERE group=:1", self).count()
	
	def canJoin(self):
		return self.spotsTaken() < self.slots

class PCApplication(db.Model):
	# For now, the PC Application will just be one big blob of text
	# created by concatenating the questions with the responses
	response = db.TextProperty(required=True)
	meeting1 = db.IntegerProperty(choices=[0,1,2])
	meeting2 = db.IntegerProperty(choices=[0,1,2])
	rejected = db.BooleanProperty(default=False)
	
class User(db.Model):
	pending = db.BooleanProperty(default=False)
	pending_code = db.StringProperty()
	email = db.StringProperty(required=True)
	password = db.StringProperty(required=True)
	first_name = db.StringProperty(required=True)
	last_name = db.StringProperty(required=True)
	project = db.ReferenceProperty(Project)
	is_pc = db.BooleanProperty(default=False)
	is_group_leader = db.BooleanProperty(default=False)
	group = db.ReferenceProperty(Group)
	pc_application = db.ReferenceProperty(PCApplication)
	phone = db.PhoneNumberProperty()
	greek_aff = db.ReferenceProperty(Greek)
	
	def joinGroup(self, the_group, autosave=True):
		self.group = the_group
		self.project = the_group.project
		if autosave:
			self.put()
	
	def makeGroupLeader(self, autosave=True):
		self.is_group_leader = True
		if autosave:
			self.put()
	
	def makePC(self, autosave=True):
		self.is_pc = True
		if autosave:
			self.put()
	
	def rejectPCApp(self, autosave=True):
		self.pc_application.rejected = True
		if autosave:
			self.pc_application.put()

	def setRandomCode(self, autosave=True):
		r = random.randint(0,1000000)
		self.pending_code = md5.new(str(r)).hexdigest()
		if autosave:
			self.put()
	
	def sendConfirmationEmail(self):
		message = mail.EmailMessage()
		message.subject = "Confirm your TEAMBuzz Account"
		message.sender = EMAIL_FROM
		message.to = self.email
		message.body = """
Hi!
	
In order to confirm your TEAMBuzz account, please
click the link below. 

%s
	    """ % (self.generateConfirmLink())

		message.send()
	
	def generateConfirmLink(self):
		confirmURL = ROOT_URL + "/confirm"
		confirmURL += "?code=" + self.pending_code
		confirmURL += "&user=" + self.email
		return confirmURL
	
	def confirm(self, autosave=True):
		self.pending = False
		# toggle their group to active if they in one
		if self.group is not None:
			self.group.pending = False
			self.group.put()
		# if self.project and not self.project.canJoin():
			# self.project = None
		if autosave:
			self.put()

# ----------------------------------------
#
# Model Forms -- we use djangoforms since it isn't user facing
#
#
# ----------------------------------------
class ProjectForm(djangoforms.ModelForm):
	class Meta:
		model = Project
		
# ----------------------------------------
#
# Form validation classes
#
# 
# ----------------------------------------
class FormValidator:
	message = None
	def verifyArguments(self, a, b):
		""" check if a contains all of the elements in b """
		return set(a) >= set(b)
		
class UserFormValidator(FormValidator):	
	def isValid(self, data):
		if not self.verifyArguments(data.keys(), ["email", "first_name", "last_name", "phone", "greek", "password"]):
			self.message = "Invalid arguments"
			return False
		
		# make sure the email isn't already being used
		resp = User.gql("WHERE email = :1", data["email"])
		if resp.count() > 0:
			self.message = "Email already in use"
			return False
		
		# make sure the greek affiliation exists
		resp = Greek.gql("WHERE name = :1", data["greek"])
		if resp.count() == 0:
			self.message = "Error with greek affiliation"
			return False
			
		return True
	
	def saveAsPendingUser(self, data):
		greek_aff = Greek.gql("WHERE name=:1", data["greek"]).get()
		pending_user = User(email=data['email'],
							password=md5.new(data['password']).hexdigest(),
							first_name = data['first_name'],
							last_name = data['last_name'],
							phone = db.PhoneNumber(data['phone']),
							greek_aff = greek_aff,
							pending = True)
		pending_user.setRandomCode()
		pending_user.put()
		# ask the user to confirm their account
		pending_user.sendConfirmationEmail()
		return pending_user
		
class GroupFormValidator(FormValidator):
	def isValid(self, data):
		if not self.verifyArguments(data.keys(), ["project", "slots", "passcode", "group_name"]):
			self.message = "Invalid arguments"
			return False
		# make sure project exists
		resp = Project.gql("WHERE name = :1", data["project"])
		if resp.count() < 1:
			self.message = "Project does not exist"
			return False
		
		# make sure slots is a valid value
		try:
			slots = int(data["slots"])
		except ValueError:
			self.message = "Invalid value for slots"
			return False
		
		# make sure project has enough open slots
		project = resp.get()
		project.calculateSpots()
		if project.spots_remaining < slots:
			self.message = "Not enough slots for your request"
			return False
		
		return True
	
	def createAsPendingGroup(self, data):
		project = Project.gql("WHERE name = :1", data['project']).get()
		
		new_group = Group(name=data["group_name"], 
						  password=data["passcode"], 
						  project=project, 
						  slots=int(data["slots"]),
						  pending=True)
		new_group.put()
		return new_group

class GroupJoinFormValidator(FormValidator):
	def isValid(self, data):
		if not self.verifyArguments(data.keys(), ["passcode", "group"]):
			self.message = "Invalid arguments"
			return False
		# make sure group exists
		try:
			group = db.get(data['group'])
		except:
			self.message = "That group doesn't exist. How strange."
			return False
		# check the passcode is correct
		if group.password != data["passcode"]:
			self.message = "Incorrect passcode."
			return False
		# check the group has open spots
		if not group.canJoin():
			self.message = "There are no spots remaining in that group."
			return False
		# make sure the group isn't pending
		if group.pending:
			self.message = "This group is pending approval."
			return False
		return True		
		
# ----------------------------------------
#
# Request Handler classes
#
#
# ----------------------------------------

class MainPage(webapp.RequestHandler):
	def get(self):
		template_data = {"phases":getPhasesForRightNow()}
		renderPageHelper(self, 'index.html', template_data)

class Projects(webapp.RequestHandler):
	def get(self):		
		projects = Project.all()
		template_values = {}
		
		# TODO: this is hideous. There must be a better way to do it
		updated_projects = []
		for p in projects:
			p.calculateSpots()
			updated_projects.append(p)
		
		template_values['projects'] = updated_projects
		template_values['can_join'] = inPhase('individual_registration')
		renderPageHelper(self, 'projects.html', template_values)
		
class Join(webapp.RequestHandler):
	
	def doJoinProject(self, user, project):
		user.project = project
		user.put()
			
	def get(self):
		if not inPhase("individual_registration"):
			errorRedirect(self, "Sorry, individual registration is not open yet.")
				
		# is the user logged in?
		sess=gmemsess.Session(self)		
		current_user = sess['current_user'] if 'current_user' in sess else None
		data = self.request.GET
		
		# make sure the project exists
		try:
			project = db.get(data['project'])
		except:
			errorRedirect(self, "The project doesn't exist. How strange.")
			return
					
		if current_user:
			the_user = User.gql("WHERE email=:1", current_user).get()
			if the_user.project:
				errorRedirect(self, "You are already in a project.")
			self.doJoinProject(the_user, project)
			self.redirect("/me")
		else:
			template_values = {}
			template_values['project'] = project
			template_values['greek'] = Greek.all().order("name")
			renderPageHelper(self, "joinaproject.html", template_values)
	
	def post(self):
		if not inPhase("individual_registration"):
			errorRedirect(self, "Sorry, individual registration is not open yet.")
			
		data = self.request.POST
		# make sure the project exists
		try:
			project = db.get(data['project'])
		except:
			errorRedirect(self, "The project doesn't exist. How strange.")
			return
		# validate the form
		validator = UserFormValidator()
		if validator.isValid(data):
			# create the user
			user = validator.saveAsPendingUser(data)
			# put them in the project
			user.project = project
			user.put()
			renderPageHelper(self, 'message.html', {"title":"Great!", "message":"We just sent you an email with the link to confirm your email address."})
		else:
			self.redirect("/error?message=" + validator.message)
			
class Login(webapp.RequestHandler):
	def testCredentials(self, user, passwd):
		""" test the provided user and password against the datastore """

		# fire the request, pending users are not considered
		login_result = User.gql("WHERE email = :1 AND password = :2 AND pending = false", user, passwd)
		
		return login_result.count() == 1
	
	def do_login(self, user, passwd):
		""" test the login, add the user to the session, and do the redirect """
		sess=gmemsess.Session(self)
		logging.info('Trying to login %s' % self.request.get('username'))
				
		# fire the login attempt
		if self.testCredentials(user, md5.new(passwd).hexdigest()):
			updateSessionForLogin(self, user)
			self.redirect('me')
		else:			
			# show error message
			template_values = {'message': "Error with login information."}
			path = os.path.join(os.path.dirname(__file__), 'login.html')
			self.response.out.write(template.render(path, template_values))
	
	def get(self):
		""" show the login form """
		template_values = {'from': self.request.get('from')}
		
		path = os.path.join(os.path.dirname(__file__), 'login.html')
		self.response.out.write(template.render(path, template_values))
	
	def post(self):
		self.do_login(self.request.get('username'), self.request.get('password'))
		
class Logout(webapp.RequestHandler):
	def get(self):
		sess=gmemsess.Session(self)
		sess.invalidate()
		path = os.path.join(os.path.dirname(__file__), 'logout.html')
		self.response.out.write(template.render(path, {}))

class Me(webapp.RequestHandler):
	def get(self):
		#TODO: PC functions
		#		email group members
		
		sess=gmemsess.Session(self)
		if 'current_user' in sess:
			the_user = User.gql("WHERE email = :1", sess['current_user']).get()
			
			template_values = {}
			
			has_app = False
			if the_user.pc_application is not None:
				template_values['has_app'] = True
			# PC view data
			if the_user.is_pc:
				template_values['is_pc'] = True
			if the_user.project is not None:
				the_user.project.calculateSpots()
				template_values['project'] = the_user.project
				template_values['volunteers'] = User.gql("WHERE project = :1", the_user.project)
			# Group data
			if the_user.group is not None:
				the_user.group.calculateSpots()
				template_values['group'] = the_user.group
				template_values['group_members'] = User.gql("WHERE group = :1", the_user.group)
			
			
			# Are they part of a project? Show them the name (and maybe more details later)
			renderPageHelper(self, 'me.html', template_values)
		else:
			# prompt for login if they aren't logged in
			renderPageHelper(self, 'login.html', {"message":'You need to login to access My TEAMBuzz.'})
		
class BeAPC(webapp.RequestHandler):
	# Add questions here and they will automatically be added to the site and the data
	# store
	questions = ["Why do you want to be a PC?",
				 "What kind of work do you want to do?"]
	
	def formatAppResponse(self):
		# concatenate all the questions and responses into one big string
		app = ""
		for j in range(len(self.questions)):
			resp = self.request.get("q" + str(j+1))
			app += "Question:\n\n"
			app += self.questions[j]
			app += "\n\nResponse:\n\n"
			app += resp
			app += "\n\n" + "-"*20 + "\n\n"
		return app
	
	def get(self):	
		""" Displays the PC Application page """
		
		if not inPhase("pc_apps"):
			errorRedirect(self, "Sorry, PC applications are not available.")
		
		template_values = {'questions': self.questions}
		
		# check if the user has already submitted an app
		sess = gmemsess.Session(self)
		if 'current_user' in sess:
			the_user = User.gql("WHERE email = :1", sess['current_user']).get()
			if the_user.pc_application is not None:
				renderPageHelper(self, 'alreadyapplied.html')
				return
		
		template_values['greek'] = Greek.all().order("name")
				
		renderPageHelper(self, 'beapc.html', template_values)
	
	def postPCAppExistingUser(self):
		validator = UserFormValidator()
		data = self.request.POST
		if validator.isValid(data):
			# submit the PC app
			new_app = PCApplication(response=self.formatAppResponse())
			new_app.put()
			# try to tie the application to their name
			the_user = User.gql("WHERE email = :1", sess['current_user']).get()

			if the_user.pc_application is None:
				the_user.pc_application = new_app
				the_user.put()
			else:
				self.redirect("/error?message=You have already submitted an app.")
				return
			self.redirect("/me")
		else:
			self.redirect("/error?message=" + validator.message)
		
	def postPCAppNewUser(self):
		validator = UserFormValidator()
		data = self.request.POST
		if validator.isValid(data):
			# save the application
			new_app = PCApplication(response=self.formatAppResponse(),
									meeting1=int(data['meeting1']),
									meeting2=int(data['meeting2']))
			new_app.put()
			user = validator.saveAsPendingUser(data)
			user.pc_application = new_app
			user.put()
			renderPageHelper(self, 'message.html', {"title":"Great!", "message":"We just sent you an email with the link to confirm your email address."})
		else:
			self.redirect("/error?message=" + validator.message)
		
	def post(self):
		""" Submits the PC application """
		if not inPhase("pc_apps"):
			errorRedirect(self, "Sorry, PC applications are not available.")
		
		# two different behaviors, depending on whether the user is logged in
		sess=gmemsess.Session(self)
		if 'current_user' in sess:
			self.postPCAppExistingUser()
		else:
			self.postPCAppNewUser()
			
class CreateGroup(webapp.RequestHandler):
	# TODO:
	# 	send email upon successful creation, encouraging to ask people to join
	#	maybe make an easy link for it? (group and passcode already filled out...)
	#	
	def get(self):
		if not inPhase("group_create"):
			errorRedirect(self, "Sorry, Group creation is not available.")
		
		template_values = {}
		
		# TODO: this is hideous. There must be a better way to do it
		projects = Project.all()
		updated_projects = []
		for p in projects:
			p.calculateSpots()
			if p.spots_remaining > 0:
				updated_projects.append(p)
			
		template_values['projects'] = updated_projects
		template_values['greek'] = Greek.all().order("name")
		
		renderPageHelper(self, 'creategroup.html', template_values)
	
	def post(self):
		if not inPhase("group_create"):
			errorRedirect(self, "Sorry, Group creation is not available.")
			
		# Validate the input
		groupValidator = GroupFormValidator()	
		if not groupValidator.isValid(self.request.POST):
			self.redirect("/error?message=" + groupValidator.message)
			return
		
		userValidator = UserFormValidator()	
		if not userValidator.isValid(self.request.POST):
			self.redirect("/error?message=" + userValidator.message)
			return
	
		data = self.request.POST
		
		logging.info("trying to great group")
		
		the_group = groupValidator.createAsPendingGroup(data)
		the_user = userValidator.saveAsPendingUser(data)
		the_user.joinGroup(the_group)
		the_user.makeGroupLeader()
		the_user.put()
		
		renderPageHelper(self, 'message.html', {"title":"Great!", "message":"We just sent you an email with the link to confirm your email address."})

class JoinGroup(webapp.RequestHandler):
	def get(self):		
		# this is fucking beautiful. <3 Python
		template_values = {
			'groups':filter(Group.canJoin, Group.all()),
			'greek':Greek.all().order("name")
		}
		renderPageHelper(self, 'joinagroup.html', template_values)

	def post(self):
		if not inPhase("group_join"):
			errorRedirect(self, "Sorry, Group joining is not available.")
		data = self.request.POST
		# Validate the input
		groupJoinValidator = GroupJoinFormValidator()	
		if not groupJoinValidator.isValid(data):
			self.redirect("/error?message=" + groupJoinValidator.message)
			return
		
		userValidator = UserFormValidator()	
		if not userValidator.isValid(data):
			self.redirect("/error?message=" + userValidator.message)
			return
					
		the_user = userValidator.saveAsPendingUser(data)
		the_user.joinGroup(db.get(data['group']))
		the_user.put()
		
		renderPageHelper(self, 'message.html', {"title":"Great!", "message":"We just sent you an email to confirm your account. Click on the link it contains and you're all set."})
			
class Contact(webapp.RequestHandler):
	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'contact.html')
		self.response.out.write(template.render(path, {}))
		
class Sponsors(webapp.RequestHandler):
	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'sponsors.html')
		self.response.out.write(template.render(path, {}))
		
class Info(webapp.RequestHandler):
	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'info.html')
		self.response.out.write(template.render(path, {}))

class Confirm(webapp.RequestHandler):
	def get(self):		
		# check to see if the code is correct
		user = self.request.get("user")
		code = self.request.get("code")
		
		resp = User.gql("WHERE email = :1 AND pending_code = :2", user, code)
		if resp.count() == 1:
			# toggle this user to active
			the_user = resp.get()
			the_user.confirm()
			the_user.put()
			updateSessionForLogin(self, the_user.email)
			self.redirect("/me")
		else:
			self.response.out.write("error")

class Init(webapp.RequestHandler):
	
	def makeBasicUser(self, username):
		u = User(first_name=username,
				 last_name=username,
				 email=username + "@gatech.edu",
				 password=md5.new(username).hexdigest())
		u.put()
		return u
		
	def get(self):
		""" init the datastore with some test data.
		
		assumes the datastore is clear.
		"""
		# a basic check to make sure the datastore is clear
		if Greek.all().count() > 0:
			return
		
		# Create a project
		kitten = Project()
		kitten.name = "Kitten Rescue"
		kitten.max_volunteers = 3
		kitten.location = "All around Atlanta."
		kitten.type_of_work = "Outdoor"
		kitten.description = "We will save kittens from trees all over Atlanta."
		kitten.put()

		soup = Project()
		soup.name = "Soup Making"
		soup.max_volunteers = 5
		soup.description = "You will make delicious soup."
		soup.put()

		huge = Project()
		huge.name = "Huge Project"
		huge.max_volunteers = 20
		huge.description = "This is a darn huge project. With 20 people what CAN'T we do?"
		huge.put()
				
		# Make a user with a pending PC app
		u = self.makeBasicUser("pending")
		pc_app = PCApplication(response="Here is the sample responses to the questions")
		pc_app.put()
		u.pc_application = pc_app
		u.put()
		
		# Put a user in the kitten project
		u = self.makeBasicUser("kitten")
		u.project = kitten
		u.put()
		
		# Create a PC for the soup project
		u = self.makeBasicUser("souppc")
		u.project = soup
		u.is_pc = True
		u.put()
		
		# Make a group for the HUGE project
		knights_group = Group(name="Knights who say Ni!", password="shrubbery", project=huge, slots=5)
		knights_group.put()
		
		leader = self.makeBasicUser("leader")
		leader.joinGroup(knights_group)
		leader.is_group_leader = True
		leader.is_pc = True
		leader.put()
		
		knights = ["lancelot", "gawain", "gallahad", "mordred"]
		for knight in knights:
			k = self.makeBasicUser(knight)
			k.joinGroup(knights_group)
			k.put()
						
		# Make a full project
		full = Project(name="Full Project",
					   max_volunteers = 5,
					   description = "This was full so quickly...")
		full.put()
		
		alphabet = "abcdefghijklmnopqrstuvwxyz"
		for j in range(5):
			u = self.makeBasicUser(alphabet[j])
			u.project = full
			u.put()
		
		# Init the Greek Affliations
		for g_name in GREEK_AFFS:
			g = Greek(name=g_name)
			g.put()

		# Add the possible phases
		phases = [
			["pc_apps", datetime.date(2008,8,1), datetime.date(2010,8,30)],
			["group_create", datetime.date(2008,8,15), datetime.date(2010,8,30)],
			["group_join", datetime.date(2008,9,15), datetime.date(2010,9,30)],
			["group_registration", datetime.date(2008,9,15), datetime.date(2010,9,30)],
			["individual_registration", datetime.date(2008,10,1), datetime.date(2010,10,15)]
		]
		for phase_args in phases:
			phase = Phase(name=phase_args[0], start_date=phase_args[1], end_date=phase_args[2])
			phase.put()
			
		# Add a group that users can join
		nice_group = Group(name="A nice group for nice people", password="nice!", project=huge, slots=5)
		nice_group.put()
		
		# Make a user that has no project
		lonely_user = self.makeBasicUser("lonely")
		lonely_user.put()
		

class TestSendMail(webapp.RequestHandler):
	def get(self):
		message = mail.EmailMessage()
		message.subject = "Test Message"
		message.sender = self.request.get("from")
		message.to = self.request.get("to")
		message.body = """
	    The emailing is working from the TEAMBuzz site.
	    """
		message.send()
		
		self.response.out.write("Tried to send mail. " + message.sender  + " to " + message.to)

class Error(webapp.RequestHandler):
	def get(self):
		message = self.request.get("message")
		renderPageHelper(self, 'error.html', {"message":message})

class VerifyEmail(webapp.RequestHandler):
	def emailExists(self, email):
		return User.gql("WHERE email = :1", email).count() > 0
		
	def get(self):
		data = self.request.GET
		email = data['email']
		if self.emailExists(email):
			self.response.out.write('false')
		else:
			self.response.out.write('true')

handlers = []
handlers.append(('/', MainPage))
handlers.append(('/projects', Projects))
handlers.append(('/contact', Contact))
handlers.append(('/join', Join))
handlers.append(('/login', Login))
handlers.append(('/logout', Logout))
handlers.append(('/init', Init))
handlers.append(('/me', Me))
handlers.append(('/beapc', BeAPC))
handlers.append(('/makeagroup', CreateGroup))
handlers.append(('/joinagroup', JoinGroup))
handlers.append(('/testsendmail', TestSendMail))
handlers.append(('/confirm', Confirm))
handlers.append(('/error', Error))
handlers.append(('/verifyemail', VerifyEmail))
handlers.append(('/admin', admin.Admin))
handlers.append(('/admin/login', admin.AdminLogin))
handlers.append(('/admin/users', admin.AdminUsers))
handlers.append(('/admin/apps', admin.AdminApps))
handlers.append(('/admin/accept', admin.Accept))
handlers.append(('/admin/reject', admin.Reject))
handlers.append(('/admin/pcprojects', admin.PCProj))
handlers.append(('/admin/projects', admin.Projects))
handlers.append(('/admin/config', admin.Config))
handlers.append(('/admin/addprojects', admin.AddProjects))
handlers.append(('/admin/init', admin.Init))
handlers.append(('/admin/contact', admin.AdminContact))
handlers.append(('/admin/stats', admin.AdminStats))
handlers.append(('/admin/usersbygroup', admin.AdminUsersByGroup))
handlers.append(('/admin/usersbygreek', admin.AdminUsersByGreek))
handlers.append(('/sponsors', Sponsors))
handlers.append(('/info', Info))

application = webapp.WSGIApplication(handlers, debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()