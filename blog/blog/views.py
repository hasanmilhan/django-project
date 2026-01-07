from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.http import Http404
from .models import Post
from .forms import EmailPostForm, CommentForm

def post_list(request):
    posts = Post.published.all()
    
    paginator = Paginator(posts, 3)  # Create a Paginator object to paginate the posts, 3 posts per page
    page_number = request.GET.get('page', 1)  # Get the current page number from the request's GET parameters, default to 1
    
    try:
        posts = paginator.get_page(page_number)  # Retrieve the posts for the current page
    except PageNotAnInteger:
        posts = paginator.get_page(1)  # If page is not an integer, deliver the first page
    except EmptyPage:
        posts = paginator.get_page(paginator.num_pages)  # If the requested page is out of range, deliver the last page of results
    
    return render(request, 'blog/post/list.html', {'posts': posts})  

def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post,
                             status=Post.Status.PUBLISHED,
                             slug=post,
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)
    comments = post.comments.filter(active=True)  # Retrieve active comments for the post
    form = CommentForm()  # Instantiate an empty comment form

    return render(
        request,
        'blog/post/detail.html',
        {
            'post': post,
            'comments': comments,
            'form': form,
        }
    )

def post_share(request, post_id):
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)  # Retrieve the post by ID and ensure it is published
    sent = False  # Initialize a variable to track if the email was sent

    if request.method == 'POST': 
        form = EmailPostForm(request.POST)  # Instantiate the form with POST data
        if form.is_valid(): 
            cd = form.cleaned_data 
            print(cd)
            post_url = request.build_absolute_uri(post.get_absolute_url())  # Build the absolute URL for the post
            subject = f"{cd['name']} ({cd['email']}) recommends you read {post.title}"  # Create the email subject
            message = f"Read {post.title} at {post_url}\n\n{cd['name']}'s comments: {cd['comments']}"  # Create the email message
            send_mail(subject, message, from_email=None, recipient_list=[cd['to']])  # Send the email
            sent = True  # Update the variable to indicate the email was sent          
    else:  # If the request method is not POST
        form = EmailPostForm()  # Instantiate an empty form
    
    return render(request, 'blog/post/share.html', {'post': post,
                                                    'form': form,
                                                    })

@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id, status=Post.Status.PUBLISHED)
    comment = None
    form = CommentForm(data=request.POST)

    if form.is_valid():
        # Create a Comment object without saving it to the database
        comment = form.save(commit=False)
        # Assign the post to the comment
        comment.post = post
        # Save the comment to the database
        comment.save()

    return render(
        request,
        'blog/post/comment.html',
        {
            'post': post,
            'form': form,
            'comment': comment,
        }
    )

