from django.shortcuts import render

def root_view(request):
	return render(request, "root/root.html")

def contact_view(request):
	return render(request, "root/contact.html")