import cgi
import os
import logging
import gmemsess
import md5
import random
import datetime

from google.appengine.ext.webapp import template
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.api import mail
from google.appengine.ext.db import djangoforms

import teambuzz

# ----------------------------------------
#
# Utility functions
#
#
# ----------------------------------------

def updateSessionForLogin(self, username):
	""" assign the username to the session """
	sess=gmemsess.Session(self)
	sess['current_user'] = username
	sess.save()

def testForAdmin(self):
	""" checks if the admin is logged in """
	sess = gmemsess.Session(self)
	if 'current_user' in sess:
		return sess['current_user'] == "admin"
	else:
		return False
		
# ----------------------------------------
#
# Request Handlers
#
#
# ----------------------------------------

class Admin(webapp.RequestHandler):
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
		
		template_values = {
			"email_from":teambuzz.EMAIL_FROM,
			"root_url":teambuzz.ROOT_URL,
			"phases":teambuzz.Phase.all().order("start_date")
		}
		if teambuzz.Greek.all().count() == 0:
			template_values['is_new'] = True
			
		
		teambuzz.renderPageHelper(self, "adminhome.html", template_values)

class AdminLogin(webapp.RequestHandler):
	def get(self):
		""" displays the login page """
		path = os.path.join(os.path.dirname(__file__), 'adminlogin.html')
		self.response.out.write(template.render(path, {}))
		
	def post(self):
		""" checks for a successful login """
		
		username = self.request.get("username")
		password = self.request.get("password")

		if username == "teambuzz" and password == "metropolitain":
			updateSessionForLogin(self, "admin")
			self.redirect("/admin")
		else:
			path = os.path.join(os.path.dirname(__file__), 'adminlogin.html')
			self.response.out.write(template.render(path, {"message":"Login failed."}))
		
class AdminUsers(webapp.RequestHandler):
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
		
		template_values = {"users": teambuzz.User.all()}
		
		path = os.path.join(os.path.dirname(__file__), 'adminusers.html')
		self.response.out.write(template.render(path, template_values))
		
	def post(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
			
class AdminContact(webapp.RequestHandler):
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
		
		template_values = {"users": teambuzz.User.all()}
		
		path = os.path.join(os.path.dirname(__file__), 'admincontact.html')
		self.response.out.write(template.render(path, template_values))
		
	def post(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
			
class AdminStats(webapp.RequestHandler):
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
			
		users =  teambuzz.User.all()
		groups =  teambuzz.Group.all()
		projects =  teambuzz.Project.all()
		
		usercount = 0
		pccount = 0
		approvedpcs = 0
		rejectedpcs = 0
		for user in users:
			usercount = usercount + 1
			if user.pc_application is not None:
				 pccount = pccount + 1
				 if user.is_pc:
				 	approvedpcs = approvedpcs + 1
		
		rejectedpcs = pccount - approvedpcs
		
		groupcount = 0
		slotstaken = 0
		spotstaken = 0
		spotsleft = 0
		for group in groups:
			groupcount = groupcount + 1
			slotstaken = slotstaken + group.slots
			spotstaken = spotstaken + teambuzz.User.gql("WHERE group=:1", group).count()
			
		spotsleft = slotstaken - spotstaken
			
		projcount = 0
		totspots = 0
		projspotsunreserved = 0
		projspotstaken = 0
		projspotsleft = 0
		for project in projects:
			projcount = projcount + 1
			totspots = totspots + project.max_volunteers
			projspotstaken = projspotstaken + teambuzz.User.gql("WHERE project=:1 and pending=false", project).count()
			
		projspotsunreserved = totspots - slotstaken
		projspotsleft = totspots - projspotstaken
		
		template_values = {
			"usercount": usercount,
			"pccount": pccount,
			"approvedpcs": approvedpcs,
			"rejectedpcs": rejectedpcs,
			"groupcount": groupcount,
			"slotstaken": slotstaken,
			"spotstaken": spotstaken,
			"spotsleft": spotsleft,
			"projcount": projcount,
			"totspots": totspots,
			"projspotsunreserved": projspotsunreserved,
			"projspotstaken": projspotstaken,
			"projspotsleft": projspotsleft
			}
		
		path = os.path.join(os.path.dirname(__file__), 'adminstats.html')
		self.response.out.write(template.render(path, template_values))
		
	def post(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
		
class AdminApps(webapp.RequestHandler):
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
		
		users = teambuzz.User.gql("WHERE pending=false")
		pc_applicants = []
		for user in users:
			if user.pc_application is not None and not user.pc_application.rejected and not user.is_pc:
				pc_applicants.append(user)
				user.response = user.pc_application.response
				
		count = 0
		for user in users:
			if user.pc_application is not None:
				count = count + 1
		
		template_values = {"pcs": pc_applicants,
		"numPCs": count
		}
		
		path = os.path.join(os.path.dirname(__file__), 'adminapps.html')
		self.response.out.write(template.render(path, template_values))
		
	def post(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
			
class AddProjects(webapp.RequestHandler):
	def get(self):
		path = os.path.join(os.path.dirname(__file__), 'adminaddprojects.html')
		self.response.out.write(template.render(path, {}))
		
	def post(self):
		data = self.request.POST
		# save the project
		new_project = teambuzz.Project(name=str(data['project_name']),
								max_volunteers=int(data['max_vols']),
								description=str(data['description']),
								location=str(data['location']),
								type_of_work=str(data['work_type']))
		new_project.put()
		
		self.message = "Project Added Successfully!"
		template_values = {'message': "Project Added Successfully!"}
		path = os.path.join(os.path.dirname(__file__), 'adminaddprojects.html')
		self.response.out.write(template.render(path, template_values))
			
class PCProj(webapp.RequestHandler):
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
			
		users = teambuzz.User.gql("WHERE pending=false")
		projects = teambuzz.Project.all()
		pc_applicants = []
		for user in users:
			if user.pc_application is not None and not user.pc_application.rejected and user.is_pc:
				pc_applicants.append(user)
		
		template_values = {"pcs": pc_applicants, "projects": projects}
		
		path = os.path.join(os.path.dirname(__file__), 'adminpcprojects.html')
		self.response.out.write(template.render(path, template_values))
		
	def post(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
			
		data = self.request.POST
		
		users = teambuzz.User.gql("WHERE pending=false")
		projects = teambuzz.Project.all()
		pc_applicants = []
		for user in users:
			if user.pc_application is not None and not user.pc_application.rejected and user.is_pc:
				if data[user.email] != "none":
					project = teambuzz.Project.gql("WHERE name = :1", data[user.email]).get()
					user.project = project
					user.save()
					
		pc_applicants = []
		for user in users:
			if user.pc_application is not None and not user.pc_application.rejected and user.is_pc:
				pc_applicants.append(user)
		
		template_values = {"pcs": pc_applicants, "projects": projects}
					
		path = os.path.join(os.path.dirname(__file__), 'adminpcprojects.html')
		self.response.out.write(template.render(path, template_values))
		
class AdminUsersByGroup(webapp.RequestHandler):
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
		
		template_values = {"projects": teambuzz.Project.all()}
		
		path = os.path.join(os.path.dirname(__file__), 'adminusersbygroup.html')
		self.response.out.write(template.render(path, template_values))
		
	def post(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
			
		data = self.request.POST
		
		project = teambuzz.Project.gql("WHERE name=:proj", proj=data['projsel']).get()
		users = teambuzz.User.gql("WHERE project=:1", project)
		count = users.count()
		
		pc_applicants = []
		for user in users:
			if user.pc_application is not None and not user.pc_application.rejected and user.is_pc:
				pc_applicants.append(user)
				
		volunteers = []
		for user in users:
			if not user.pc_application or user.pc_application.rejected:
				volunteers.append(user)
		
		template_values = {"users": volunteers, "project": project, "count": count, "pcs": pc_applicants, "projects": teambuzz.Project.all()}
					
		path = os.path.join(os.path.dirname(__file__), 'adminusersbygroup.html')
		self.response.out.write(template.render(path, template_values))
		
class AdminUsersByGreek(webapp.RequestHandler):
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
		
		template_values = {"greeks": teambuzz.Greek.all()}
		
		path = os.path.join(os.path.dirname(__file__), 'adminusersbygreek.html')
		self.response.out.write(template.render(path, template_values))
		
	def post(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
			
		data = self.request.POST
		
		greek = teambuzz.Greek.gql("WHERE name=:greek", greek=data['greeksel']).get()
		users = teambuzz.User.gql("WHERE greek_aff=:1", greek)
		count = users.count()
		
		template_values = {"users": users, "count": count, "greeks": teambuzz.Greek.all(), "greek": greek}
					
		path = os.path.join(os.path.dirname(__file__), 'adminusersbygreek.html')
		self.response.out.write(template.render(path, template_values))


class Accept(webapp.RequestHandler):
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
		# try to fetch the user	
		data = self.request.GET
		try:
			user = db.get(data['user'])
		except:
			teambuzz.errorRedirect(self, "Invalid user")
		# make the user a pc
		user.makePC()
		
		message = mail.EmailMessage()
		message.subject = "Your TEAMBuzz PC Application has been Approved!"
		message.sender = teambuzz.EMAIL_FROM
		message.to = user.email
		message.body = """
Hello!

Your application to be a Project Coordinator for TEAMBuzz has just been approved!
A project will be assigned to you shortly!

Thank you for volunteering your time for the Atlanta Community!

Regards,
TEAMBuzz Steering Committee

	    """
		message.send()
		
		self.redirect("/admin/apps")

class Reject(webapp.RequestHandler):
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")			
		# try to fetch the user	
		data = self.request.GET
		try:
			user = db.get(data['user'])
		except:
			teambuzz.errorRedirect(self, "Invalid user")
		# reject their app
		user.rejectPCApp()
		
		message = mail.EmailMessage()
		message.subject = "Your TEAMBuzz PC Application has been Rejected"
		message.sender = teambuzz.EMAIL_FROM
		message.to = user.email
		message.body = """
Hello,

Your application to be a Project Coordinator for TEAMBuzz has just been rejected
If you have any questions in regards to this decision, please contact our chair of project coordinators,
Marleen Kanagawa, at mkanagawa@gatech.edu.

Thank you for your willingness to be of service.

Regards,
TEAMBuzz Steering Committee

	    """
		message.send()
		
		self.redirect("/admin/apps")
		
		
class Projects(webapp.RequestHandler):
# This doesn't do anything useful right now, I am just playing with it.
# MAP 8/28
	def get(self):
		if not testForAdmin(self):
			self.redirect("/admin/login")
			
		self.response.out.write("""
		<html><body>
		<form method="post" action="/">
		<table>
		""")
		self.response.out.write(teambuzz.ProjectForm())
		self.response.out.write("""
		</table>
		<input type="submit" />
		</form>
		</body></html>
		""")
	def post(self):
		pass
		
class Config(webapp.RequestHandler):
	def get(self):
		teambuzz.renderPageHelper(self, "adminconfig.html")
		
class Init(webapp.RequestHandler):
	def get(self):
		# only init if the greek entity is empty
		if teambuzz.Greek.all().count() > 0:
			return
		
		# Init the Greek Affliations
		for g_name in teambuzz.GREEK_AFFS:
			g = teambuzz.Greek(name=g_name)
			g.put()

		# Add the possible phases
		phases = [
			["pc_apps", datetime.date(2009,8,31), datetime.date(2009,9,14), "PC Application period"],
			["group_create", datetime.date(2009,9,14), datetime.date(2009,9,28), "Group creation period"],
			["group_join", datetime.date(2009,9,14), datetime.date(2009,9,28), "Group joining period"],
			["group_registration", datetime.date(2009,9,14), datetime.date(2009,9,28), "Group registration period (usually start of group creation and end of group joining)"],
			["individual_registration", datetime.date(2009,9,28), datetime.date(2009,10,10), "Individual registration"]
		]
		for phase_args in phases:
			phase = teambuzz.Phase(name=phase_args[0], start_date=phase_args[1], end_date=phase_args[2], description=phase_args[3])
			phase.put()
			
		self.redirect("/admin")