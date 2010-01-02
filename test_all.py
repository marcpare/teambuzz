# TODO:
# Clea datastore between tests. 
# tearing down doesn't work. It gets a little complicated to
# deal with data from other tests. 
#
#

# test using nosetests --with-gae
import random
import unittest
import md5
import datetime
import teambuzz

def createNiceRandomString(num_chars):
	letters = "abcdefghijklmnopqrstuvwxyz"
	ret = ""
	for j in range(num_chars):
		ret += letters[random.randrange(0,len(letters))]
	return ret

def createARandomUser():
	return createRandomUsers(1)[0]

def createRandomUsers(num_users):
	""" creates some random users, making sure not to duplicate email addresses"""
	# generate the email addresses
	used_emails = set()
	added = 0
	while added < num_users:
		email = createNiceRandomString(5)
		if email not in used_emails:
			used_emails.add(email)
			added+=1
			
	# create the users
	ret = []
	for email in used_emails:
		u = teambuzz.User(email=email, 
				 password=createNiceRandomString(10),
				 first_name = createNiceRandomString(5),
				 last_name = createNiceRandomString(5))
		ret.append(u)
	return ret

class TestValidation(unittest.TestCase):
	def testVerifyArguments(self):
		f = teambuzz.FormValidator()
		
		a = ["foo", "bar"]
		b = ["foo"]
		c = ["foo", "bar", "camp"]
		d = ["foo", "bar"]
		e = []
		self.assert_(f.verifyArguments(a, b))
		self.assert_(f.verifyArguments(a, a))
		self.assert_(f.verifyArguments(a, d))
		self.assert_(f.verifyArguments(a, e))
		self.assert_(not f.verifyArguments(a, c))
	
	def testUserForm(self):
		uf = teambuzz.UserFormValidator()
		# add a Greek house
		g = teambuzz.Greek(name="DX")
		g.put()
		
		# bad data input
		data = {'foo':'bar'}
		self.assert_(not uf.isValid(data))
		
		# good input
		data = {u'email':'test@aol.com', 
				u'first_name':'test', 
				u'last_name':'test', 
				u'phone':'test', 
				u'greek':'DX', 
				u'password':'test'}
		self.assert_(uf.isValid(data))

		# non existant greek house
		data = {u'email': 'test@aol.com', 
				u'first_name':'test', 
				u'last_name':'test', 
				u'phone':'test', 
				u'greek':'BLACK HOLE', 
				u'password':'test'}
		self.assert_(not uf.isValid(data))
		
		# duplicate email address
		u = createARandomUser()
		u.put()
		data = {u'email': u.email, 
				u'first_name':'test', 
				u'last_name':'test', 
				u'phone':'test', 
				u'greek':'DX', 
				u'password':'test'}
		self.assert_(not uf.isValid(data))
	
	def testGroupForm(self):
		gf = teambuzz.GroupFormValidator()
		
		empty_project = teambuzz.Project(name="A project", max_volunteers=10)
		empty_project.put()
		
		full_project = teambuzz.Project(name="Full project", max_volunteers=0)
		full_project.put()
		
		# valid data
		data = {u'project':empty_project.name, 
				u'slots':'10', 
				u'passcode':'test'}
		# too many slots requested
		data = {u'project':empty_project.name, 
				u'slots':'20', 
				u'passcode':'test'}
		self.assert_(not gf.isValid(data))
		# invalid project name
		data = {u'project':'Not a project', 
				u'slots':'10', 
				u'passcode':'test'}
		self.assert_(not gf.isValid(data))
		# invalid slots value
		data = {u'project':empty_project.name, 
				u'slots':'asdf', 
				u'passcode':'test'}
		self.assert_(not gf.isValid(data))
		# project with not enough open slots
		data = {u'project':full_project.name, 
				u'slots':'10', 
				u'passcode':'test'}
		self.assert_(not gf.isValid(data))
		
	def testVerifyEmail(self):
		u = createARandomUser()
		u.put()
		verifier = teambuzz.VerifyEmail()
		self.assert_(verifier.emailExists(u.email))
		self.assert_(not verifier.emailExists(u.email + "s"))
		

class TestLogin(unittest.TestCase):
	def testBadLogin(self):
		# create a user, use a different password
		a_user = createARandomUser()
		a_user.put()
		
		login = teambuzz.Login()
		result = login.testCredentials(a_user.email, a_user.password + ".")
		self.assert_(not result)
	
	def testGoodLogin(self):
		# create a user, use the password
		a_user = createARandomUser()
		a_user.put()
		
		login = teambuzz.Login()
		result = login.testCredentials(a_user.email, a_user.password)
		self.assert_(result)
		
	def testPendingUsers(self):
		# create a user, make them pending
		a_user = createARandomUser()
		a_user.pending = True
		a_user.put()
		
		login = teambuzz.Login()
		result = login.testCredentials(a_user.email, a_user.password)
		self.assert_(not result)

class TestCreate(unittest.TestCase):
	
	def testConfirmation(self):
		# make sure groups get confirmed when the user confirms
		p = teambuzz.Project(name="Project", max_volunteers=3)
		p.put()		
		u = createARandomUser()
		u.put()
		gf = teambuzz.GroupFormValidator()
		g = gf.createAsPendingGroup({
			"group_name":"Test Group",
			"passcode":"asdf",
			"project":p.name,
			"slots":2 })
		u.joinGroup(g)
		u.makeGroupLeader()
		u.confirm()
		self.assert_(teambuzz.Group.gql("WHERE name=:1 and pending=false", g.name).count() == 1)

class TestPhases(unittest.TestCase):
	def testPhasesForDate(self):
		p = teambuzz.Phase(name="june", start_date=datetime.date(1800,6,1), end_date=datetime.date(1800,6,30))
		p.put()
		# check for empty phase list
		res = teambuzz.getPhasesForDate(datetime.date(1800,5,1))
		self.assert_(len(res) == 0)
		
		res = teambuzz.getPhasesForDate(datetime.date(1800,7,1))
		self.assert_(len(res) == 0)
		
		# check for intersecting one phase
		res = teambuzz.getPhasesForDate(datetime.date(1800,6,1))
		self.assert_(len(res) == 1)
		res = teambuzz.getPhasesForDate(datetime.date(1800,6,30))
		self.assert_(len(res) == 1)
		
		# intersecting multiple phases
		p = teambuzz.Phase(name="july", start_date=datetime.date(1800,7,1), end_date=datetime.date(1800,7,31))
		p.put()
		p = teambuzz.Phase(name="midsummer", start_date=datetime.date(1800,7,15), end_date=datetime.date(1800,8,15))
		p.put()
		p = teambuzz.Phase(name="august", start_date=datetime.date(1800,8,1), end_date=datetime.date(1800,8,31))
		p.put()
		
		res = teambuzz.getPhasesForDate(datetime.date(1800,7,16))
		self.assert_(len(res) == 2)

	def testPhasesForRightNow(self):
		today = datetime.date.today()
		oneday = datetime.timedelta(days=1)
		twodays = datetime.timedelta(days=2)
		p = teambuzz.Phase(name=u"goingonnow", start_date=today-oneday, end_date=today+oneday)
		p.put()
		p = teambuzz.Phase(name=u"happenedalready", start_date=today-twodays, end_date=today-oneday)
		p.put()
		
		res = teambuzz.getPhasesForRightNow()
		self.assertEqual(res, [u"goingonnow"])

class TestSlotCounts(unittest.TestCase):
# This might just be the most important part of all of the tests since it
# is both easy to mess up and has the potential to piss off users
	def testSlotCounts(self):
		today = datetime.date.today()
		oneday = datetime.timedelta(days=1)		
		current_phase = teambuzz.Phase(name="pc_apps", start_date=today-oneday, end_date=today+oneday)
		current_phase.put()
		
		shrubbery = teambuzz.Project(name="Shrubbery Trimming", max_volunteers=30)
		shrubbery.put()
		
		some_vols = createRandomUsers(5)
		for j in range(len(some_vols)):
			some_vols[j].project = shrubbery
			some_vols[j].put()
		
		shrubbery.calculateSpots()
		# Basic test of user count
		self.assertEqual(shrubbery.spots_taken, 5)
		
		pending_user = createARandomUser()
		pending_user.pending = True
		pending_user.project = shrubbery
		pending_user.put()
		shrubbery.calculateSpots()
		# Make sure pending users aren't included
		self.assertEqual(shrubbery.spots_taken, 5)
		
		pending_user.pending = False
		pending_user.put()
		shrubbery.calculateSpots()
		# Turn the user on, make sure it is included
		self.assertEqual(shrubbery.spots_taken, 6)
		
		group = teambuzz.Group(name="Knights", 
					  		   slots=3,
					  		   project=shrubbery,
							   pending=False)
		group.put()
		shrubbery.calculateSpots()
		# make sure adding a group doesn't affect the pc app phase
		self.assertEqual(shrubbery.spots_taken, 6)
		
		current_phase.name = "individual_registration"
		current_phase.put()
		# make sure groups don't affect the individual registration phase
		self.assertEqual(shrubbery.spots_taken, 6)
		
		current_phase.name = "group_registration"
		current_phase.put()		
		shrubbery.calculateSpots()
		# make sure count reflects group
		self.assertEqual(shrubbery.spots_taken, 9)
		
		group = teambuzz.Group(name="Pending Knights", 
					  		   slots=3,
					  		   project=shrubbery,
							   pending=True)
		group.put()
		shrubbery.calculateSpots()
		# make sure pending groups don't count
		self.assertEqual(shrubbery.spots_taken, 9)
	
		u = createARandomUser()
		u.joinGroup(group)
		u.project = shrubbery
		u.put()
		shrubbery.calculateSpots()
		# make sure users that have joined a group don't increase the count
		self.assertEqual(shrubbery.spots_taken, 9)
		
		current_phase.name = "individual_registration"
		current_phase.put()
		shrubbery.calculateSpots()
		# make sure the user in the group is counted now
		self.assertEqual(shrubbery.spots_taken, 7)

class TestGroupFilter(unittest.TestCase):
	def testFilter(self):
		# clear the Group database
		teambuzz.db.delete(teambuzz.Group.all())
		
		group = teambuzz.Group(name="Knights 1", 
					  		   slots=0,
							   pending=False)
		group.put()
		group = teambuzz.Group(name="Knights 2", 
					  		   slots=3,
							   pending=False)
		group.put()
		groups = teambuzz.Group.all()
		# make sure only the two groups are in the datastore
		self.assertEqual(groups.count(), 2)
		
		groups = filter(teambuzz.Group.canJoin, teambuzz.Group.all())
		# test the filtering with the canJoin function
		self.assertEqual(len(groups), 1)

class TestConfirmOver(unittest.TestCase):
	def testConfirmationAfterFullProject(self):
		p = teambuzz.Project(name="To Fill", max_volunteers=1)
		p.put()
		some_vols = createRandomUsers(5)
		
		some_vols[0].pending = True
		some_vols[0].project = p
		
		p.calculateSpots()
		self.assertEqual(p.spots_taken, 0)
		
		some_vols[0].confirm()
		p.calculateSpots()
		self.assertEqual(p.spots_taken, 1)
		
		some_vols[1].project = p
		some_vols[1].confirm()
		p.calculateSpots()
		self.assertEqual(p.spots_taken, 1)
		
class TestGroupJoinFormValidator(unittest.TestCase):
	def testBasicInputs(self):
		# clear the Group database
		teambuzz.db.delete(teambuzz.Group.all())
		
		group1 = teambuzz.Group(name="Knights 1", 
							    password="knight1",
					  		    slots=0,
							    pending=False)
		group1.put()
		group2 = teambuzz.Group(name="Knights 2", 
		   						password="knight2",
					  		    slots=3,
							    pending=False)
		group2.put()
		group3 = teambuzz.Group(name="Knights 3", 
		   						password="knight3",
					  		    slots=3,
							    pending=True)
		group3.put()
		
		gfv = teambuzz.GroupJoinFormValidator()
		data = {
			"group":"asdf",
			"passcode":"knight2"
		}
		# test for group that doesn't exist
		self.assert_(not gfv.isValid(data))
		
		data['group'] = group2.key()
		# test for group that does exist
		gfv.isValid(data)
		self.assert_(gfv.isValid(data))
		
		data['passcode'] = group2.password + "XX"
		# test for group with incorrect password
		self.assert_(not gfv.isValid(data))
		
		data['group'] = group1.key()
		data['passcode'] = group1.password
		# group with no open spots
		self.assert_(not gfv.isValid(data))
		
		data['group'] = group3.key()
		data['passcode'] = group3.password
		# a pending group
		self.assert_(not gfv.isValid(data))