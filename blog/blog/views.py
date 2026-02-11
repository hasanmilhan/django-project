from django.shortcuts import render, get_object_or_404
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.http import Http404
from .models import Post
from .forms import EmailPostForm, CommentForm, SearchForm
from taggit.models import Tag

def post_list(request, tag_slug=None):
    posts = Post.published.all()
    tag = None
    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        posts = posts.filter(tags__in=[tag])  # Filter posts by the specified tag

    
    paginator = Paginator(posts, 3)  # Create a Paginator object to paginate the posts, 3 posts per page
    page_number = request.GET.get('page', 1)  # Get the current page number from the request's GET parameters, default to 1
    
    try:
        posts = paginator.get_page(page_number)  # Retrieve the posts for the current page
    except PageNotAnInteger:
        posts = paginator.get_page(1)  # If page is not an integer, deliver the first page
    except EmptyPage:
        posts = paginator.get_page(paginator.num_pages)  # If the requested page is out of range, deliver the last page of results
    
    return render(request, 'blog/post/list.html', {'posts': posts,
                                                   'tag': tag})  

def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post,
                             status=Post.Status.PUBLISHED,
                             slug=post,
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)
    comments = post.comments.filter(active=True)  # Retrieve active comments for the post
    form = CommentForm()  # Instantiate an empty comment form

    # List of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)  # Get the IDs of the tags associated with the post
    similar_posts = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)  # Find other published posts that share these tags, excluding the current post
    similar_posts = similar_posts.annotate(same_tags=Count('tags')).order_by('-same_tags', '-publish')[:4]  # Annotate with the number of shared tags and order by that count and publish date, limiting to 4 posts

    return render(
        request,
        'blog/post/detail.html',
        {
            'post': post,
            'comments': comments,
            'form': form,
            'similar_posts': similar_posts,
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

def post_search(request):
    form = SearchForm()
    query = None
    results = []
    
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = Post.published.annotate(
                similarity=TrigramSimilarity('title', query) + TrigramSimilarity('body', query),  # Annotate each post with a similarity score based on trigram similarity
            ).filter(similarity__gt=0.1).order_by('-similarity')  # Order the results by relevance rank in descending order

    return render(request, 'blog/post/search.html', {'form': form,
                                                     'query': query,
                                                     'results': results})

