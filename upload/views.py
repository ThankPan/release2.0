from django.shortcuts import render,render_to_response
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import loginUser, registerUser
from django.contrib.auth.models import User,Group
from django.contrib.auth import logout
from django.core.exceptions import ObjectDoesNotExist
from .models import Homework, Record
from django.http import JsonResponse,HttpResponseRedirect, Http404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import StreamingHttpResponse,HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django import forms
import codecs

# Create your views here.
@csrf_exempt
def login_user(request):
    """
    登陆操作部分
    :return: 登陆成功跳转至个人主页，失败则提示失败信息。
    """
    if request.method == 'POST':
        form = loginUser(request.POST)
        if form.is_valid():
            username = form.cleaned_data['Username']
            password = form.cleaned_data['Password']
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                if user.groups.filter(name='Student').exists():
                    return HttpResponseRedirect('/upload/Account/')
                else:
                    return HttpResponseRedirect('/upload/Teacher/')
            else:
                messages.error(request, '登录失败！')
    else:
        form = loginUser()
    return render(request, 'login.html')

def register_user(request):
    print(request)
    if request.method == 'POST':
        form = registerUser(request.POST)
        print(form)
        if form.is_valid():
            print("OK")
            if form.cleaned_data['Password']==form.cleaned_data['ConfirmPass']:
                username = form.cleaned_data['Username']
                if User.objects.filter(username__exact=username).count()==0:
                    password = form.cleaned_data['Password']
                    user = User.objects.create_user(username=username, password=password)
                    user.groups.add(Group.objects.get(name='Student'))
                    user.save()
                    messages.success(request, '注册成功!')
                else:
                    messages.error(request, "该用户名已经被注册")
            else:
                messages.error(request, '两次输入的密码不匹配')

    else:
        form = registerUser()
    return render(request, 'register.html')

@csrf_exempt
def Account(request):
    """
    个人主页
    :return: 渲染个人主页
    """

    return render(request,'Account.html')

@csrf_exempt
def get_homeworks(request):
    """
    处理数据库中作业相关信息，将其转化为json文件以供前端渲染
    :return: 返回一个包含所有作业信息的json文件
    """
    homeworks = Homework.objects.all()
    resultdict = {}
    dict = []
    count = homeworks.count()
    for h in homeworks:
        dic = {}
        dic['id'] = h.pk
        dic['des'] = h.Description
        dic['duedate'] = h.Deadline.strftime('%Y-%m-%d,%H:%M:%S')
        if Record.objects.filter(Homework=h).filter(Student=request.user).count() > 0:
            dic['status'] = "已提交"
            if Record.objects.filter(Homework=h).get(Student=request.user).status == 2:
                            dic['grade'] = Record.objects.filter(Homework=h).get(Student=request.user).Scores
            else:
                            dic['grade'] = '老师尚未打分'
        else:
            dic['status'] = "未提交"
        dict.append(dic)
    resultdict['data'] = dict
    resultdict['code'] = 0
    resultdict['msg'] = ""
    resultdict['count'] = count
    return JsonResponse(resultdict, safe=False)

@csrf_exempt
def upload_file(request,pk):
    """
    处理上传文件
    :return: 如果上传成功并成功保存，则返回一个json文件，其中statu=1表示成功，status=0则表示失败
    """
    file = request.FILES.get('file')
    filename = '%s/%s' % (settings.MEDIA_ROOT, file.name)
    print(file.name)
    with open(filename, 'wb')as f:
        for ff in file.chunks():
            f.write(ff)

    ret = {'status': 1}
    uploaded = Homework.objects.get(pk=pk)
    Record.objects.create(Homework=uploaded, Student=request.user, Upload_time=timezone.now(), File=file).save()

    return JsonResponse(ret)

@csrf_exempt
def Teacher(request):
    return render(request, 'Teacher.html')

@csrf_exempt
def get_teacher_homeworks(request):
    homeworks = Homework.objects.all()
    resultdict={}
    dict=[]
    count=homeworks.count()
    for h in homeworks:
        dic={}
        dic['id']=h.pk
        dic['des']=h.Description
        dic['duedate']=h.Deadline.strftime('%Y-%m-%d,%H:%M:%S')
        dict.append(dic)
    resultdict['data'] = dict
    resultdict['code'] = 0
    resultdict['msg'] = ""
    resultdict['count'] = count
    return JsonResponse(resultdict, safe=False)

@csrf_exempt
def assign(request):
    if request.method == 'POST':
        Homework.objects.create(Description=request.POST.get('Description'), Deadline=request.POST.get('Deadline')).save()
        ret={'status': 1}
        return render(request, 'Teacher.html')
    else:
        return HttpResponseRedirect('/')

def logout_view(request):
    logout(request)
    messages.success(request, "您已退出！")
    return render(request, 'logout.html')

def batch_log(request):
    return

@csrf_exempt
def download_homework(request, pk, id):
    def file_iterator(file, chunk_size=512):
        try:
            with codecs.open(file, "r", "gbk") as f:
                while True:
                    c = f.read(chunk_size)
                    if c:
                        yield c
                    else:
                        break
        except:
            with codecs.open(file, "r", "utf8") as f:
                while True:
                    c = f.read(chunk_size)
                    if c:
                        yield c
                    else:
                        break

    records =Record.objects.filter(Homework_id__exact=pk).get(Student__username__exact=id)
    file = records.File
    print(file.name)
    records.status = 4
    records.save()
    filename = r'%s/%s' % (settings.MEDIA_ROOT, file.name)
    print(filename)
    response = StreamingHttpResponse(file_iterator(filename))
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = "attachment;filename='{0}'".format(file)
    print(response['Content-Disposition'])
    return response

@csrf_exempt
def Record_List(request, pk):
    deadline = Homework.objects.get(pk=pk).Deadline
    records = Record.objects.filter(Homework_id__exact=pk).filter(Upload_time__lte=deadline)
    resultdict = {}
    dict = []
    total = records.count()
    page = request.POST.get('page')
    rows = request.POST.get('limit')
    i = (int(page) - 1) * int(rows)
    j = (int(page) - 1) * int(rows) + int(rows)
    records=records[i:j]
    resultdict['total']=total
    for r in records:

        dic = {}
        dic['id'] = r.Student.username
        dic['homework'] = r.Homework.Description
        dic['status'] = r.get_status_display()
        if r.status == 2:
            dic['score'] = r.Scores
        dict.append(dic)


    resultdict['data'] = dict
    resultdict['code'] = 0
    resultdict['msg'] = ""
    resultdict['count'] = total
    return JsonResponse(resultdict, safe=False)

@csrf_exempt
def Specific(request, pk):
    return render(request, 'Record.html', {'pk':pk})

@csrf_exempt
def grade(request,pk,id):
    if request.method == 'POST':
        record = Record.objects.filter(Homework_id__exact=pk).get(Student__username__exact=id)
        record.Scores = request.POST.get('grade')
        record.status = 2
        record.save()
        return HttpResponseRedirect(reverse('des', args=(pk, )))

@csrf_exempt
def late_homeworks(request,pk):
    deadline = Homework.objects.get(pk=pk).Deadline
    records = Record.objects.filter(Homework_id__exact=pk).filter(Upload_time__gt=deadline)
    resultdict = {}
    dict = []
    total = records.count()
    page = request.POST.get('page')
    rows = request.POST.get('limit')
    i = (int(page) - 1) * int(rows)
    j = (int(page) - 1) * int(rows) + int(rows)
    records = records[i:j]
    resultdict['total'] = total
    for r in records:
        dic = {}
        dic['id'] = r.Student.username
        dic['homework'] = r.Homework.Description
        dic['status'] = r.get_status_display()
        if r.status == 2:
            dic['score'] = r.Scores
        dict.append(dic)

    resultdict['data'] = dict
    resultdict['code'] = 0
    resultdict['msg'] = ""
    resultdict['count'] = total
    return JsonResponse(resultdict, safe=False)

class ChangeForm(forms.Form):
    username = forms.CharField(label='用户名')
    old_password = forms.CharField(label='原密码',widget=forms.PasswordInput())
    new_password = forms.CharField(label='新密码',widget=forms.PasswordInput())

@csrf_exempt
def change_pass(request):
    if request.method == 'POST':
        uf = ChangeForm(request.POST)
        if uf.is_valid():
            username = uf.cleaned_data['username']
            old_password = uf.cleaned_data['old_password']
            new_password = uf.cleaned_data['new_password']

            ##判断用户原密码是否匹配
            user = authenticate(username=username, password=old_password)
            if user is not None:
                u=User.objects.get(username=username)
                u.set_password(new_password)
                u.save()  ##如果用户名、原密码匹配则更新密码
                messages.success(request, '修改成功!')
            else:
                messages.error(request, "请检查原密码与用户名是否输入正确!")

    else:
        uf = ChangeForm()
    return  render(request, 'change.html', {'form':uf})